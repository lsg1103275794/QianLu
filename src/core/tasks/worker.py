"""
Async task worker for processing analysis tasks using SQLite backend.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone # Use timezone-aware
import yaml # Added import
from pathlib import Path # Added import
import os
import json
import re # Added import for regex

from src.core.tasks.models import TaskStatus
# Import TaskManager instance (now using SQLite)
from src.core.tasks.manager import task_manager # No Redis key needed
from src.utils.logging import logger
from src.config.api_manager import api_manager
from src.providers.factory import get_handler
from src.utils.config import UPLOAD_DIR # <--- 1. 导入 UPLOAD_DIR
from src.utils import file_utils # <--- 导入 file_utils

# --- Define template directory path (similar to analysis.py) ---
try:
    _worker_file_path = Path(__file__).resolve()
    _src_dir = _worker_file_path.parent.parent.parent # Should be 'src' directory
    _project_root_dir = _src_dir.parent # Should be the project root
    TEMPLATE_DIR = _project_root_dir / "config" / "prompt_templates"
    if not TEMPLATE_DIR.is_dir():
        logger.error(f"Template directory not found by worker: {TEMPLATE_DIR}")
        TEMPLATE_DIR = None
    else:
         logger.info(f"Worker located template directory: {TEMPLATE_DIR}")
except Exception as path_e:
    logger.error(f"Error resolving template directory path in worker: {path_e}", exc_info=True)
    TEMPLATE_DIR = None
# ----------------------------------------------------------------

# --- Helper function to load template content ---
def _load_template_content(template_id: str) -> Optional[Dict[str, Any]]:
    """Loads the full content of a single template file by its ID."""
    if not TEMPLATE_DIR:
        logger.error("Template directory path is not configured in worker.")
        return None
        
    templates_dir = TEMPLATE_DIR
    possible_suffixes = ['.yaml', '.yml'] # Focus on YAML for now
    target_file: Optional[Path] = None

    for suffix in possible_suffixes:
        potential_path = templates_dir / (template_id + suffix)
        if potential_path.is_file():
            target_file = potential_path
            break
    
    if not target_file:
        logger.warning(f"Template file not found for ID: {template_id} in {templates_dir}")
        return None

    try:
        logger.debug(f"Worker loading content for template: {target_file.name}")
        content_str = target_file.read_text(encoding='utf-8')
        data: Dict[str, Any] = yaml.safe_load(content_str)
                
        if not isinstance(data, dict):
            logger.warning(f"Template file {target_file.name} content is not a dictionary.")
            return None
            
        return data
    except yaml.YAMLError as ye:
         logger.error(f"Invalid YAML in template file {target_file.name}: {ye}")
         return None # Indicate failure to load due to format error
    except Exception as e:
        logger.error(f"Error loading single template file {target_file.name}: {e}", exc_info=True)
        return None
# ---------------------------------------------


class TaskWorker:
    def __init__(self):
        self.is_running = False
        self.worker_task = None
        if task_manager is None:
             # Should not happen if manager initialization is checked properly at startup
             raise RuntimeError("TaskManager (SQLite) is not initialized. Worker cannot start.")
        self.task_manager = task_manager # Use the imported instance

    async def start(self):
        """Start the task worker."""
        if self.is_running:
            return
        
        self.is_running = True
        self.worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Task worker started")
        
    async def stop(self):
        """Stop the task worker."""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            self.worker_task = None
        logger.info("Task worker stopped")
        
    async def _worker_loop(self):
        """Run the worker loop."""
        # 添加一个计数器，用于控制日志记录频率
        empty_loops_counter = 0
        max_silent_loops = 720  # 约1小时静默期（假设每5秒一次循环）
        
        while self.is_running:
            try:
                # 获取要处理的任务
                tasks = await self.task_manager.get_pending_tasks(limit=10)
                
                # 减少频繁记录"没有任务"的日志
                if len(tasks) == 0:
                    empty_loops_counter += 1
                    # 只有在开发模式下，且每max_silent_loops次循环才记录一次"空闲"日志
                    if empty_loops_counter >= max_silent_loops and os.environ.get("DEV_MODE") == "1":
                        logger.debug(f"[WORKER_LOOP] Worker has been idle for approximately {empty_loops_counter * 5} seconds.")
                        empty_loops_counter = 0  # 重置计数器
                else:
                    # 有任务时重置计数器并继续正常记录
                    empty_loops_counter = 0
                    # 使用更简洁的日志格式
                    logger.info(f"[WORKER_LOOP] Processing {len(tasks)} tasks.")
                
                # 仅当有任务时才记录处理逻辑
                if tasks:
                    for task in tasks:
                        # 避免已处理任务重复记录日志
                        if task.status not in [TaskStatus.PENDING]:
                            continue
                        
                        # 获取任务类型（如果可用）
                        task_type_info = "Unknown"
                        if task.metadata and 'task_type' in task.metadata:
                            task_type_info = task.metadata['task_type']
                        elif task.metadata and 'type' in task.metadata: # 备用键
                            task_type_info = task.metadata['type']
                        
                        logger.info(f"Processing task {task.id} (Type: {task_type_info})")
                        
                        try:
                            # 更新任务状态为处理中
                            task.status = TaskStatus.RUNNING
                            await self.task_manager.update_task(task)

                            # Process the task
                            await self._process_task(task.id, task.metadata)
                        except Exception as e:
                            logger.error(f"Error processing task {task.id}: {e}", exc_info=True)
                            # Update task with error details
                            await self.task_manager.update_task(
                                task.id,
                                status=TaskStatus.FAILED,
                                error=str(e)
                            )
            except asyncio.CancelledError:
                logger.info("Worker loop cancelled.")
                break # Exit loop if cancelled
            except Exception as e:
                logger.error(f"Error in task worker loop: {e}", exc_info=True)
                await asyncio.sleep(10)  # Wait longer on error
                
            # 每次循环结束后，休眠一段时间后再继续
            # 减少轮询频率，从5秒增加到10秒，降低日志生成频率
            await asyncio.sleep(10)
    
    async def _process_task(self, task_id: str, metadata: Optional[Dict[str, Any]]):
        """Process a single task."""
        if not metadata:
            await self.task_manager.update_task(
                task_id, 
                status=TaskStatus.FAILED,
                error="Task metadata is missing"
            )
            return
            
        logger.info(f"Processing task {task_id}: {metadata.get('analysis_type', 'unknown')}")
        
        try:
            # Mark task as running
            success = await self.task_manager.update_task(
                task_id,
                status=TaskStatus.RUNNING,
                progress=0.1
            )
            if not success:
                 logger.warning(f"Failed to mark task {task_id} as RUNNING (maybe already processed?). Skipping.")
                 return

            # Get task parameters more robustly
            # Try to get params from metadata.params, if not, assume metadata itself contains the params.
            task_params_dict = metadata.get("params")
            if not isinstance(task_params_dict, dict):
                logger.debug(f"[TASK_DEBUG {task_id}] 'params' key not found in metadata or not a dict. Assuming metadata itself holds the parameters.")
                task_params_dict = metadata # Use metadata directly
            else:
                logger.debug(f"[TASK_DEBUG {task_id}] Found 'params' key in metadata.")

            text_from_direct_input = task_params_dict.get("text", "")
            file_path_relative = task_params_dict.get("file_path")

            logger.info(f"[TASK_DEBUG {task_id}] Direct input text length: {len(text_from_direct_input)}. File path: {file_path_relative}. Params source: {'metadata.params' if isinstance(metadata.get('params'), dict) else 'metadata'}")

            actual_text_to_analyze = text_from_direct_input

            # --- 2. 实现文件内容加载 ---
            if not actual_text_to_analyze and file_path_relative:
                logger.info(f"[TASK_DEBUG {task_id}] Text input is empty, attempting to load from file_path: {file_path_relative}")
                if not UPLOAD_DIR: # Sanity check
                    logger.error(f"[TASK_DEBUG {task_id}] UPLOAD_DIR is not configured in worker. Cannot load file.")
                    raise ValueError("UPLOAD_DIR not configured, cannot process file.")
                
                # Ensure file_path_relative is a string and not None before Path operations
                if not isinstance(file_path_relative, str):
                    logger.error(f"[TASK_DEBUG {task_id}] file_path_relative is not a string: {type(file_path_relative)}")
                    raise ValueError("Invalid file_path type received in task parameters.")

                full_file_path = UPLOAD_DIR / file_path_relative
                logger.info(f"[TASK_DEBUG {task_id}] Attempting to load content from full path: {full_file_path}")

                if not full_file_path.is_file():
                    logger.error(f"[TASK_DEBUG {task_id}] File not found at resolved path: {full_file_path}")
                    # Try to list contents of UPLOAD_DIR and its 'temp' subdir for debugging
                    try:
                        logger.debug(f"Contents of UPLOAD_DIR ({UPLOAD_DIR}): {os.listdir(UPLOAD_DIR)}")
                        temp_subdir = UPLOAD_DIR / "temp"
                        if temp_subdir.is_dir():
                            logger.debug(f"Contents of UPLOAD_DIR/temp ({temp_subdir}): {os.listdir(temp_subdir)}")
                    except Exception as list_err:
                        logger.error(f"Could not list UPLOAD_DIR contents for debugging: {list_err}")
                    raise ValueError(f"File not found at path: {file_path_relative}")
                
                try:
                    # Use the same utility as files.py for consistency
                    actual_text_to_analyze = file_utils.load_file_content(full_file_path, logger)
                    logger.info(f"[TASK_DEBUG {task_id}] Successfully loaded text from file. Length: {len(actual_text_to_analyze)}")
                except Exception as e:
                    logger.error(f"[TASK_DEBUG {task_id}] Error loading content from file {full_file_path}: {e}", exc_info=True)
                    raise ValueError(f"Error reading file content from {file_path_relative}: {e}")
            
            # --- 校验最终是否有文本内容 ---
            if not actual_text_to_analyze:
                # This check now happens *after* attempting to load from file
                logger.error(f"[TASK_DEBUG {task_id}] Final text to analyze is empty after checking direct input and file_path.")
                raise ValueError("Text/File content is missing after attempting all sources.")


            analysis_type = task_params_dict.get("analysis_type", "simple")
            options = task_params_dict.get("options", [])
            api_provider = metadata.get("api_provider")
            model = metadata.get("model")
            template_id = metadata.get("template") # Get the template ID/name
            
            # Validate parameters (some might be redundant now or covered by earlier checks)
            if not analysis_type: raise ValueError("Analysis type is missing")
            # The main text/file content check is now done above
            if not options: raise ValueError("Analysis options are missing")

            # Update progress
            await self.task_manager.update_task(task_id, progress=0.2)
            
            # Process based on analysis type
            result_data = {}
            
            # --- Actual Analysis Logic --- 
            if analysis_type == "basic":
                # Basic analysis logic remains the same
                logger.debug(f"Performing basic analysis for task {task_id}")
                result_data = { "status": "success", "message": "Basic analysis completed." } # Placeholder
                await self.task_manager.update_task(task_id, progress=0.9)

            elif analysis_type == "literature" or analysis_type == "deep":
                if not api_provider: raise ValueError(f"{analysis_type} analysis requires an API provider")
                    
                logger.debug(f"Performing {analysis_type} analysis for task {task_id} using {api_provider}/{model} with template ID: {template_id}")
                await self.task_manager.update_task(task_id, progress=0.5)
                
                handler = get_handler(api_provider)
                if not handler: raise ValueError(f"API provider {api_provider} not found or not configured")
                
                # --- Prepare prompt using template if available ---
                prompt_to_send = None # Initialize the final prompt
                if template_id:
                    logger.info(f"Attempting to load template content for ID: {template_id}")
                    template_data = _load_template_content(template_id)
                    if template_data:
                        # 首先尝试使用full_prompt_template
                        if "full_prompt_template" in template_data:
                            final_prompt_str = template_data["full_prompt_template"]
                            logger.debug(f"[TASK_DEBUG {task_id}] Using full_prompt_template. Original: '{final_prompt_str[:200]}...'")
                        # 如果没有full_prompt_template，尝试使用prompt
                        elif "prompt" in template_data:
                            final_prompt_str = template_data["prompt"]
                            logger.warning(f"'full_prompt_template' not found in {template_id}. Falling back to 'prompt' field.")
                            logger.debug(f"[TASK_DEBUG {task_id}] Using prompt. Original: '{final_prompt_str[:200]}...'")
                        else:
                            logger.warning(f"Template {template_id} loaded, but neither 'full_prompt_template' nor 'prompt' key is available.")
                            final_prompt_str = None
                        
                        # 如果成功获取了模板字符串，执行替换操作
                        if final_prompt_str:
                            # 替换{input_text}占位符
                            if "{input_text}" in final_prompt_str:
                                final_prompt_str = final_prompt_str.replace("{input_text}", actual_text_to_analyze) # Use the definitive text
                                logger.debug(f"[TASK_DEBUG {task_id}] Replaced {{input_text}} in prompt.")
                            # 处理{{text}}占位符（主题分析模板用此格式）
                            elif "{{text}}" in final_prompt_str:
                                final_prompt_str = final_prompt_str.replace("{{text}}", actual_text_to_analyze)
                                logger.debug(f"[TASK_DEBUG {task_id}] Replaced {{{{text}}}} in prompt.")
                            else:
                                logger.warning(f"[TASK_DEBUG {task_id}] Template {template_id} does not contain {{input_text}} or {{{{text}}}} placeholder.")
                            
                            prompt_to_send = final_prompt_str
                    else:
                        logger.warning(f"Failed to load template content for ID: {template_id}. Proceeding without template-based prompt.")

                if not prompt_to_send:
                    # Fallback or default prompt if template not used or failed to load
                    # This part might need adjustment based on desired behavior
                    logger.info(f"[TASK_DEBUG {task_id}] No template prompt constructed, using direct text for analysis (if applicable).")
                    # For deep analysis, usually a structured prompt is expected. 
                    # If direct `actual_text_to_analyze` is okay for the LLM, this is fine.
                    # Otherwise, a default structured prompt might be needed here.
                    # For now, we assume the handler can take the raw text if no specific prompt is built.
                    # However, for literary analysis, a template is almost always required.
                    # If template_id was provided but loading failed, this is an issue.
                    if template_id: # If a template was expected but failed
                        raise ValueError(f"Failed to load expected template '{template_id}' for deep analysis.")
                    else: # If no template was specified, this is likely an error for deep/literary analysis
                        logger.warning(f"Deep/Literary analysis called without a template ID for task {task_id}. This might lead to poor results.")
                        # Defaulting to sending the raw text as prompt, but this is usually not ideal for structured analysis.
                        prompt_to_send = actual_text_to_analyze


                # For analysis tasks, use a lower temperature for more deterministic output
                analysis_kwargs = {}
                if analysis_type == "literature" or analysis_type == "deep":
                    analysis_kwargs['temperature'] = 0.2
                    logger.debug(f"Setting temperature to 0.2 for {analysis_type} analysis.")

                completion = await handler.generate_text(
                    prompt=prompt_to_send,
                    model=model, 
                    **analysis_kwargs
                )
                
                # 过滤<think>标签及其内容
                if isinstance(completion, str):
                    # 检查是否包含<think>标签
                    if "<think>" in completion:
                        logger.warning(f"发现模型输出中包含<think>标签，将进行过滤处理")
                        # 移除<think>开始到</think>结束的内容（包括标签）
                        completion = re.sub(r'<think>[\s\S]*?</think>', '', completion)
                        # 如果没有</think>标签，只有<think>开头，则移除<think>及其后所有内容
                        if "<think>" in completion:
                            completion = re.sub(r'<think>[\s\S]*', '', completion)
                        # 清理可能的空行
                        completion = re.sub(r'\n\s*\n', '\n\n', completion)
                        completion = completion.strip()
                        logger.info(f"过滤<think>标签后的内容长度: {len(completion)} 字符")
                
                # Process completion (check for JSON, etc.)
                # This part might need to be similar to OllamaLocalHandler's JSON extraction if applicable
                try:
                    processed_completion_for_storage = None
                    parsing_error_message = None # Store any parsing related errors

                    if isinstance(completion, str):
                        json_str = None
                        # 1. Try to find ```json ... ``` block
                        match_markdown = re.search(r"```json\\s*([\\s\\S]*?)\\s*```", completion, re.DOTALL)
                        if match_markdown:
                            json_str = match_markdown.group(1).strip() # Get content and strip whitespace
                            logger.debug(f"Extracted JSON from ```json ... ``` for task {task_id}.")
                        else:
                            # 2. If no markdown, try to find raw JSON object/array.
                            # The problematic regex was here, attempting to parse JSON-like structures.
                            # Original: r"^\\s*(\\{(?:[^{}]|\\{[^{}]*\\})*\\}|\\s*\\[(?:[^[\\]]|\\[[^\\[\\]]*\\])*\\])\\s*$"
                            # Corrected: Reduced \\s to \\s, \\{ to \\{, etc. and adjusted character class escaping for clarity and correctness.
                            # The goal is to match a string that is entirely a JSON object or a JSON array.
                            # Object part: \\{(?:[^{}]|\\{[^{}]*\\})*\\}
                            # Array part: \\[(?:[^\\\[\\\]]|\\[[^\\\[\\\]]*\\])*\\]
                            # The character class [^\\\[\\\]] means "any character that is not a [ or a ]".
                            # In a Python raw string, this becomes r"[^\[\]]".
                            match_raw = re.search(r"^\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\s*\[(?:[^\[\]]|\[[^\[\]]*\])*\])\s*$", completion, re.DOTALL)
                            if match_raw:
                                json_str = match_raw.group(1).strip()
                                logger.debug(f"Extracted raw JSON block for task {task_id}.")
                            else:
                                # Fallback: Try to find any JSON-like structure if strict patterns fail
                                # This is a bit more lenient, finding the first '{...}' or '[...]'
                                lenient_match_raw = re.search(r"(\\{[\\s\\S]*\\}|\\[[\\s\\S]*\\])", completion, re.DOTALL)
                                if lenient_match_raw:
                                    json_str = lenient_match_raw.group(1).strip()
                                    logger.debug(f"Extracted JSON with lenient regex for task {task_id}.")
                        
                        if json_str:
                            try:
                                processed_completion_for_storage = json.loads(json_str)
                                logger.info(f"Successfully parsed extracted JSON for task {task_id}.")
                            except json.JSONDecodeError as je:
                                parsing_error_message = f"Invalid JSON extracted: {je}. Extracted string (first 200): {json_str[:200]}"
                                logger.warning(f"{parsing_error_message} for task {task_id}.")
                                # Store the problematic string for debugging, but flag as error
                                processed_completion_for_storage = {
                                    "error": "Invalid JSON structure from model after extraction.",
                                    "details": f"Attempted to parse: {json_str[:200]}...",
                                    "original_model_output_preview": completion[:200]+"..."
                                }
                        else:
                            # NO JSON block found by any regex attempt
                            parsing_error_message = "No valid JSON block found in model output."
                            logger.warning(f"{parsing_error_message} Task {task_id}. Raw output (first 200): {completion[:200]}")
                            
                            # 修改：对于非JSON输出，特别是theme_symbolism_analysis模板，将其包装为有效的JSON
                            if template_id and template_id == "theme_symbolism_analysis":
                                logger.info(f"检测到主题与象征分析模板，将文本内容包装为JSON返回")
                                processed_completion_for_storage = {
                                    "content": completion,
                                    "format": "markdown",
                                    "template_id": template_id
                                }
                            # 如果是深度文本分析，也接受纯文本输出
                            elif analysis_type == "deep" or analysis_type == "literature":
                                logger.info(f"深度文本分析接受纯文本输出，将文本内容包装为JSON返回")
                                processed_completion_for_storage = {
                                    "content": completion,
                                    "format": "markdown" if "###" in completion or "**" in completion else "text",
                                    "analysis_type": analysis_type
                                }
                            else:
                                # 其他情况仍然报错
                                processed_completion_for_storage = {
                                    "error": "Model output was not valid JSON.",
                                    "details": f"Model returned non-JSON text: {completion[:200]}..."
                                }
                    
                    elif isinstance(completion, dict) or isinstance(completion, list):
                        # Completion from handler is already structured
                        processed_completion_for_storage = completion
                        logger.info(f"LLM completion for task {task_id} was already structured (not a string).")
                    else:
                        # Unknown completion type
                        parsing_error_message = f"Unexpected completion type from handler: {type(completion)}"
                        logger.error(f"{parsing_error_message} for task {task_id}.")
                        processed_completion_for_storage = {
                            "error": "Unknown output format from model.",
                            "details": f"Received type {type(completion)}: {str(completion)[:200]}..."
                        }

                    result_data = processed_completion_for_storage
                    
                    # If there was a parsing error message and the result is a dict, add it
                    if parsing_error_message and isinstance(result_data, dict) and "parsing_error_info" not in result_data and "error" not in result_data :
                         result_data["parsing_error_info"] = parsing_error_message

                except Exception as parse_e: # Catch-all for unexpected errors during this new logic
                    logger.error(f"Critical error during completion processing/parsing for task {task_id}: {parse_e}", exc_info=True)
                    result_data = {"error": "Failed to process model output due to an internal error.", "details": str(parse_e)}
                # --- END OF NEW JSON PROCESSING LOGIC ---

            # Update task with result
            logger.info(f"[WORKER_PROCESS {task_id}] Task completed successfully. Result: {str(result_data)[:200]}...")
            await self.task_manager.update_task(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                progress=100.0, # Ensure progress is 100.0 for completion
                result=result_data
            )
            
        except ValueError as ve: # Catch our specific ValueErrors
            logger.error(f"ValueError during task {task_id} processing: {ve}", exc_info=True)
            await self.task_manager.update_task(task_id, status=TaskStatus.FAILED, error=str(ve))
        except Exception as e:
            logger.error(f"[WORKER_PROCESS {task_id}] Error processing task: {e}", exc_info=True)
            await self.task_manager.update_task(
                task_id,
                status=TaskStatus.FAILED,
                error=f"Unhandled exception: {str(e)}"
            )

# --- Create a global worker instance ---
# Now initialized in startup after manager connects
task_worker = None # Initialize as None

def initialize_worker():
    global task_worker # Keep this to modify the global var for other potential uses
    if task_manager: # Check if task_manager itself is initialized
        instance = TaskWorker()
        task_worker = instance # Assign to global variable
        logger.info("TaskWorker instance created.")
        return instance # Return the created instance
    else:
        logger.critical("Cannot create TaskWorker instance because TaskManager is not available.")
        return None # Return None if creation failed

# We will call initialize_worker() from startup.py after task_manager connects 