"""
Analysis-related API routes.
"""
import os
import yaml
import json
from fastapi import APIRouter, HTTPException, status, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from src.api.models.analysis import AnalysisRequest, AnalysisResponse, AnalysisTemplate
from src.core.tasks.manager import task_manager
from src.core.tasks.models import TaskStatus
from src.providers.factory import get_handler
from src.config.api_manager import api_manager
from src.utils.logging import logger
from src.utils.error_handler import raise_http_error, handle_error
from pathlib import Path
import requests
import aiohttp
import httpx

# Attempt to import the specific error class
try:
    from src.validation.error_handler import APIResponseError
except ImportError:
    logger.warning("Could not import APIResponseError from src.validation.error_handler. Falling back to base Exception for sync analysis error handling.")
    # Define a placeholder if import fails to avoid crashing, although functionality will be limited
    class APIResponseError(Exception):
         def __init__(self, provider_name: str, status_code: int = 500, details: str = "Unknown API response error"):
              self.provider_name = provider_name
              self.status_code = status_code
              self.details = details
              super().__init__(f"{provider_name} API Response Error: {status_code} - {details}")

# --- Router Definition ---
router = APIRouter(prefix="/analysis", tags=["analysis"])

# Get project root directory and CLEAN IT IMMEDIATELY
# Go up one more level to get the actual project root, not the 'src' directory
_raw_project_root_dir = Path(__file__).resolve().parent.parent.parent.parent
_cleaned_root_str = str(_raw_project_root_dir).replace('\u200b', '')
PROJECT_ROOT_DIR = Path(_cleaned_root_str)
logger.info(f"Cleaned Project Root Directory: {PROJECT_ROOT_DIR}")

# Define template paths
模板目录 = PROJECT_ROOT_DIR / "config" / "prompt_templates"
文学模板文件名 = "文学模板.yaml" # Basic literature template
文学模板路径 = 模板目录 / 文学模板文件名

# --- Template Loading Functions ---

def _load_single_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Loads the full content of a single template file by its ID."""
    templates_dir = 模板目录
    possible_suffixes = ['.yaml', '.yml', '.json']
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
        logger.debug(f"Loading full content for template: {target_file.name}")
        content_str = target_file.read_text(encoding='utf-8')
        data: Dict[str, Any] = {}
        
        if target_file.suffix.lower() == '.json':
            data = json.loads(content_str)
        elif target_file.suffix.lower() in ['.yaml', '.yml']:
            try:
                data = yaml.safe_load(content_str)
            except yaml.YAMLError as ye:
                logger.error(f"Invalid YAML in template file {target_file.name}: {ye}")
                return None # Indicate failure to load due to format error
                
        # Ensure it's a dictionary
        if not isinstance(data, dict):
            logger.warning(f"Template file {target_file.name} content is not a dictionary.")
            return None
            
        return data
    except Exception as e:
        logger.error(f"Error loading single template file {target_file.name}: {e}", exc_info=True)
        return None

def load_analysis_templates() -> List[AnalysisTemplate]:
    """Load analysis templates from all YAML/JSON files in the config/prompt_templates directory."""
    templates = []
    # Use the correct TEMPLATE_DIR defined at module level
    templates_dir = 模板目录
    logger.info(f"Loading templates from directory: {templates_dir}")

    if not templates_dir.is_dir():
        logger.warning(f"Template directory not found: {templates_dir}")
        return []

    try:
        file_count = 0
        possible_suffixes = ['.yaml', '.yml', '.json'] # Accept multiple formats
        
        for item in templates_dir.iterdir():
             if item.is_file() and item.suffix.lower() in possible_suffixes:
                file_count += 1
                logger.debug(f"Processing template file: {item.name}")
                try:
                    template_id = item.stem # Use filename as ID
                    content_str = item.read_text(encoding='utf-8')
                    data: Dict[str, Any] = {}
                    
                    if item.suffix.lower() == '.json':
                        data = json.loads(content_str)
                    elif item.suffix.lower() in ['.yaml', '.yml']:
                         try:
                              data = yaml.safe_load(content_str)
                         except yaml.YAMLError as ye:
                             logger.warning(f"Skipping invalid YAML file {item.name}: {ye}")
                             continue # Skip this file
                    
                    # Gracefully handle cases where parsing might result in non-dict (e.g., empty file)
                    if not isinstance(data, dict):
                         logger.warning(f"Skipping template file {item.name} as content is not a valid dictionary structure.")
                         continue

                    # Flexible name extraction
                    name_keys = ['name', 'template_name', 'title']
                    template_name = template_id # Default to ID
                    for key in name_keys:
                        if isinstance(data.get(key), str) and data[key].strip():
                            template_name = data[key].strip()
                            break
                        # Check nested metadata common pattern
                        elif isinstance(data.get('metadata'), dict) and isinstance(data['metadata'].get(key), str) and data['metadata'][key].strip():
                             template_name = data['metadata'][key].strip()
                             break
                        
                    # Flexible description extraction
                    desc_keys = ['description', 'desc', 'summary', 'purpose']
                    template_description = None
                    for key in desc_keys:
                        if isinstance(data.get(key), str) and data[key].strip():
                            template_description = data[key].strip()
                            break
                         # Check nested metadata
                        elif isinstance(data.get('metadata'), dict) and isinstance(data['metadata'].get(key), str) and data['metadata'][key].strip():
                             template_description = data['metadata'][key].strip()
                             break

                    # Only require ID and Name (which defaults to ID) to be listed
                    templates.append(AnalysisTemplate(
                        id=template_id,
                        name=template_name,
                        description=template_description or "暂无描述", # Provide default
                        prompt_template="" # We don't load/validate prompt here for listing
                    ))
                    logger.debug(f"Successfully processed template '{template_id}' ({template_name})")

                except Exception as file_e:
                    logger.error(f"Failed to process template file {item.name}: {str(file_e)}", exc_info=True)

        logger.info(f"Found {file_count} potential template files, successfully processed {len(templates)} templates.")
        templates.sort(key=lambda t: t.name) # Sort by name
        return templates

    except Exception as e:
        logger.error(f"Error loading analysis templates: {str(e)}", exc_info=True)
        return []

def load_literature_template() -> Dict[str, Any]:
    """Load the basic literature analysis template YAML file (文学模板.yaml)."""
    try:
        if not 文学模板路径.is_file():
            logger.error(f"模板文件未找到: {文学模板路径}")
            raise_http_error(status.HTTP_404_NOT_FOUND, "文学模板文件未找到。")

        with open(文学模板路径, 'r', encoding='utf-8') as f:
            template_content = yaml.safe_load(f)

        if not template_content:
            logger.error(f"模板文件为空或无效: {文学模板路径}")
            raise_http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "文学模板文件为空或无效。")

        return template_content
    except yaml.YAMLError as e:
        logger.exception(f"解析 YAML 文件时出错 {文学模板路径}: {e}")
        raise_http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, f"解析模板文件时出错: {e}")
    except Exception as e:
        logger.exception(f"加载模板时发生意外错误 {文学模板路径}: {e}")
        handle_error(e)

# --- Literature Analysis Prompt Building Helpers (Old version for 文学模板.yaml) ---

def find_instruction_by_id(template: Dict[str, Any], dimension_id: str) -> str | None:
    """根据层级 ID (如 'cat.subcat.param') 在模板中查找 instruction"""
    parts = dimension_id.split('.')
    current_level = template.get('categories', [])
    target_instruction = None

    try:
        for i, part_id in enumerate(parts):
            found = False
            if isinstance(current_level, list):
                for item in current_level:
                    if item.get('id') == part_id:
                        if i == len(parts) - 2:
                            parameters = item.get('parameters', [])
                            param_id_to_find = parts[-1]
                            for param in parameters:
                                if param.get('id') == param_id_to_find:
                                    target_instruction = param.get('instruction')
                                    found = True
                                    break
                            if found: break
                        elif 'subcategories' in item:
                            current_level = item['subcategories']
                            found = True
                            break
                        else:
                            return None
                if not found: return None
            else:
                return None
            if target_instruction: break
    except Exception as e:
        logger.error(f"在模板中查找 ID '{dimension_id}' 时出错: {e}")
        return None

    return target_instruction

def build_analysis_prompt(text: str, selected_dimensions: List[str], template: Dict[str, Any]) -> str:
    """根据用户选择的维度和文本构建最终的分析提示"""
    instructions = []
    for dim_id in selected_dimensions:
        instruction = find_instruction_by_id(template, dim_id)
        if instruction:
            parts = dim_id.split('.')
            dim_name = parts[-1]
            instructions.append(f"针对维度 '{dim_name}':\n{instruction.strip()}\n")
        else:
            logger.warning(f"未能在模板中找到维度 ID '{dim_id}' 对应的指令。")

    if not instructions:
        raise_http_error(status.HTTP_400_BAD_REQUEST, "未能根据所选维度生成有效的分析指令。")

    prompt = (
        f"请对以下文本进行文学分析：\n\n"
        f"\"\"\"文本内容开始\"\"\"\n{text}\n\"\"\"文本内容结束\"\"\"\n\n"
        f"请根据以下要求进行分析，并以 Markdown 格式输出结果。每个维度的分析请分开呈现：\n\n"
        f"{'---\n'.join(instructions)}"
        f"\n请严格按照上述要求进行细致分析，确保结果的专业性和准确性。"
    )

    logger.debug(f"构建的 Prompt: \n{prompt[:500]}...")
    return prompt

# --- API Endpoints ---

@router.get("/templates", response_model=List[AnalysisTemplate], summary="获取所有通用分析模板列表")
async def get_analysis_templates():
    """Get available general analysis templates (from config/prompt_templates)."""
    return load_analysis_templates()

@router.get("/templates/{template_id}", response_model=Dict[str, Any], summary="获取单个通用分析模板的完整内容")
async def get_single_template(template_id: str):
    """Get the full content of a specific general analysis template by its ID."""
    template_data = _load_single_template(template_id)
    if template_data is None:
        raise HTTPException(status_code=404, detail=f"Template with ID '{template_id}' not found or failed to load.")
    return template_data

# Endpoint for the OLD basic literature template (if still needed elsewhere)
@router.get("/templates/literature", summary="获取基础文学分析模板结构 (旧版)")
async def 获取文学模板():
    """获取基础文学分析提示模板 (文学模板.yaml) 的结构。"""
    try:
        return load_literature_template()
    except HTTPException as http_exc: # Catch potential 404 from load_literature_template
        raise http_exc
    except Exception as e:
        handle_error(e) # Use generic handler for other errors

@router.post("/analyze/async", response_model=dict, summary="开始异步通用文本分析任务")
async def start_analysis_async(request: AnalysisRequest):
    """Start a new asynchronous general text analysis task."""
    # --- 新增校验：确保提供了文本或文件路径 ---
    if not request.text and not request.file_path:
        logger.warning("Async analysis request missing both text and file_path.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="必须提供文本内容 (text) 或文件路径 (file_path) 进行分析。")
    # --- 校验结束 ---

    # 验证API提供商和模型 (如果需要深度分析)
    if request.analysis_type == 'deep' and request.api_provider:
        # 检查 Provider 是否配置 (使用 api_manager)
        if not api_manager.is_provider_configured(request.api_provider):
            raise HTTPException(status_code=400, detail=f"API provider '{request.api_provider}' is not configured")
        
        # 检查 Model 是否可用 (如果指定了模型)
        if request.model:
            try:
                handler = get_handler(request.api_provider)
                available_models = await handler.get_available_models()
                if request.model not in available_models:
                    raise HTTPException(status_code=400, detail=f"Model '{request.model}' is not available for provider '{request.api_provider}'")
            except Exception as e:
                logger.warning(f"获取模型列表失败 for {request.api_provider}: {e}")
                # 不强制模型验证失败，可能只是列表获取失败，让后端任务尝试
                pass 

    # 准备传递给任务管理器的数据
    task_payload = {
        "analysis_type": request.analysis_type,
        "text": request.text,
        "file_path": request.file_path, # 确保模型包含 file_path
        "options": request.options, # 确保模型包含 options
        "template": request.template,
        "api_provider": request.api_provider,
        "model": request.model
        # 可以根据需要添加其他参数
    }

    # 创建任务
    try:
        # 确保 task_manager 已正确初始化 (假设它在某处是单例)
        from src.core.tasks.manager import task_manager # 确保导入
        task = await task_manager.create_task(task_payload)
        # logger.info(f"Created analysis task {task.id} with payload: {task_payload}")
        # Modified logging: Avoid logging full text payload to prevent encoding/length issues
        log_payload = {k: v for k, v in task_payload.items() if k != 'text'}
        log_payload['text_length'] = len(task_payload.get('text', ''))
        logger.info(f"Created analysis task {task.id} with summarized payload: {log_payload}")
    except Exception as e:
        logger.error(f"Failed to create analysis task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create analysis task: {str(e)}")

    # 返回任务ID
    return {"task_id": task.id}

@router.post("/analyze", response_model=dict, summary="执行同步文本分析")
async def analyze_text(request: AnalysisRequest):
    """
    同步执行文本分析（非异步API）。
    对于小到中等大小的文本内容，直接返回分析结果。
    """
    logger.info(f"收到同步文本分析请求: analysis_type={request.analysis_type}")
    
    # Basic validation (remains the same)
    if not request.text and not request.file_path:
        raise HTTPException(status_code=400, detail="请提供文本内容或文件路径")
    if not request.options:
        raise HTTPException(status_code=400, detail="请选择至少一个分析选项")
    if request.analysis_type == 'deep':
        if not request.api_provider:
            raise HTTPException(status_code=400, detail="深度分析需要提供API提供商")
        if not api_manager.is_provider_configured(request.api_provider):
            raise HTTPException(status_code=400, detail=f"API提供商'{request.api_provider}'未配置")

    # Read text from file if necessary (TODO: Implement file reading logic)
    text_to_analyze = request.text
    if not text_to_analyze and request.file_path:
         logger.warning("File path provided to sync analyze, but file reading not implemented.")
         # Placeholder: raise error or attempt reading
         raise HTTPException(status_code=501, detail="File reading for sync analysis not implemented yet.")
         
    if not text_to_analyze:
         raise HTTPException(status_code=400, detail="No text content available for analysis.")

    result = {}
    if request.analysis_type == 'basic':
        try:
            # Keep using async if the basic analyzer is async
            from src.core.analyzers.basic_analyzer import perform_basic_analysis
            result = await perform_basic_analysis(text_to_analyze, request.options)
        except ImportError:
             logger.error("Basic analyzer not found or import failed.")
             raise HTTPException(status_code=501, detail="Basic analysis is not available.")
        except Exception as e:
            logger.error(f"基础分析失败: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"基础分析处理失败: {str(e)}")
    
    elif request.analysis_type == 'deep':
        # Use synchronous requests for deep analysis in this sync endpoint
        logger.info(f"Performing synchronous deep analysis using provider: {request.api_provider}")
        
        # Get the handler for the selected provider
        try:
            handler = get_handler(request.api_provider)
        except ValueError as e:
            logger.error(f"Failed to get handler for provider '{request.api_provider}': {e}")
            raise HTTPException(status_code=500, detail=str(e))
            
        # Get provider config for default model (if needed)
        provider_config = api_manager.get_config(request.api_provider) 
        target_model = request.model or (provider_config.get('default_model') if provider_config else None)
        if not target_model:
             logger.warning(f"No specific model selected and no default model found for {request.api_provider}. Behavior depends on provider handler.")
             # Let the handler decide the default if model is None

        # --- Create the prompt with Chinese instruction --- 
        prompt_with_instruction = f"请仔细分析以下文本，并用中文进行回答：\n\n{text_to_analyze}"
        # ------------------------------------------------
        
        try:
            # Check which method the handler supports (prefer generate_text for simplicity here)
            if hasattr(handler, 'generate_text'):
                logger.debug(f"Using handler.generate_text for {request.api_provider}")
                # Note: handler methods are async, so this route MUST be async
                completion = await handler.generate_text(
                    prompt=prompt_with_instruction, 
                    model=target_model # Pass None if no model selected/default
                )
            elif hasattr(handler, 'chat'): # Fallback to chat if generate_text not available
                logger.debug(f"Using handler.chat for {request.api_provider}")
                messages = [
                     # Optional: Add a system message if beneficial
                     # {"role": "system", "content": "请用中文回答。"}, 
                     {"role": "user", "content": prompt_with_instruction}
                 ]
                chat_response = await handler.chat(
                    messages=messages,
                    model=target_model # Pass None if no model selected/default
                )
                # Extract content from chat response (handle potential variations)
                if isinstance(chat_response, dict) and 'content' in chat_response:
                     completion = chat_response['content']
                elif isinstance(chat_response, object) and hasattr(chat_response, 'content'):
                     completion = chat_response.content
                elif isinstance(chat_response, str):
                      completion = chat_response
                else:
                      logger.warning(f"Unexpected chat response format from handler: {type(chat_response)}")
                      completion = str(chat_response) # Fallback to string representation
            else:
                 logger.error(f"Handler for provider '{request.api_provider}' does not support 'generate_text' or 'chat'.")
                 raise HTTPException(status_code=501, detail=f"Sync analysis not supported for provider '{request.api_provider}'.")

            # --- 新增：处理流式/分片/异常内容 ---
            final_content = None
            try:
                if hasattr(completion, '__aiter__') or hasattr(completion, '__iter__'):
                    content_chunks = []
                    if hasattr(completion, '__aiter__'):
                        async for chunk in completion:
                            if isinstance(chunk, dict) and 'content' in chunk:
                                content_chunks.append(chunk['content'])
                            elif isinstance(chunk, str):
                                content_chunks.append(chunk)
                    else:
                        for chunk in completion:
                            if isinstance(chunk, dict) and 'content' in chunk:
                                content_chunks.append(chunk['content'])
                            elif isinstance(chunk, str):
                                content_chunks.append(chunk)
                    final_content = ''.join(content_chunks)
                else:
                    final_content = completion.strip() if isinstance(completion, str) else str(completion)
            except Exception as e:
                logger.error(f"[内容拼接异常] Sync分析 LLM结果拼接失败: {e}")
                final_content = str(completion)

            # --- 新增：内容完整性校验 ---
            if not final_content or len(final_content.strip()) < 30:
                logger.warning(f"Sync分析结果内容异常短，可能被截断或出错。")
                result_note = "内容异常短，可能被截断或出错"
            elif final_content.strip().endswith("..."):
                logger.warning(f"Sync分析结果以'...'结尾，可能被截断。")
                result_note = "内容以'...'结尾，可能被截断"
            else:
                result_note = ""

            result = {
               "deep_analysis_report": final_content,
               "analyzed_options": request.options,
               "provider": request.api_provider,
               "model": target_model,
               "result_note": result_note
            }

        # Catch potential exceptions from the handler (e.g., connection errors, API errors)
        except APIResponseError as e: # Catch specific API errors if handler raises them
             logger.error(f"API provider {request.api_provider} returned an error (sync): {e.details}")
             raise HTTPException(status_code=e.status_code or 502, detail=f"AI provider error: {e.details}")
        except httpx.TimeoutException as e: # If handler uses httpx and raises timeout
             logger.error(f"Timeout error connecting to {request.api_provider} (sync): {e}")
             raise HTTPException(status_code=504, detail=f"Request to AI provider timed out.")
        except httpx.RequestError as e: # If handler uses httpx and raises connection error
              logger.error(f"Connection error to {request.api_provider} (sync): {e}")
              raise HTTPException(status_code=503, detail=f"Failed to connect to AI provider: {e}")
        except Exception as e:
            logger.error(f"同步深度分析失败 for {request.api_provider}: {e}", exc_info=True)
            # Use the centralized error handler for unexpected errors
            handle_error(e)
            # raise HTTPException(status_code=500, detail=f"同步深度分析处理失败: {str(e)}") # handle_error might raise its own HTTPException

    else:
        raise HTTPException(status_code=400, detail=f"不支持的分析类型: {request.analysis_type}")
    
    # Return the result (structure might need adjustment based on analysis type)
    return result

# --- REMOVE OLD PROVIDER/MODEL ROUTES (duplicates in providers.py) ---
# @router.get("/providers", ...)
# async def get_providers(): ...
# @router.get("/models/{provider}", ...)
# async def get_models(provider: str): ... 