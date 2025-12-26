"""
Core logic for V2 multi-dimensional literature analysis.
"""
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from src.utils.logging import logger

# --- Path Definitions ---
# Assuming the script runs relative to the project root structure
# Adjust if necessary based on actual execution context
try:
    # Go up three levels from src/core/literature_analyzer.py to get project root
    PROJECT_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
except NameError:
    # Fallback for environments where __file__ might not be defined reliably
    PROJECT_ROOT_DIR = Path.cwd() # Or define a more robust way if needed
    logger.warning(f"Could not determine project root from __file__, using cwd: {PROJECT_ROOT_DIR}")

专业模板目录 = PROJECT_ROOT_DIR / "config" / "promptPRO"
详细文学模板文件名 = "文学创作多维分析模板 v2.yaml"
详细文学模板路径 = 专业模板目录 / 详细文学模板文件名

# --- Template Loading ---
def load_detailed_literature_template() -> Optional[Dict[str, Any]]:
    """Load the V2 multi-dimensional literature analysis template YAML file."""
    template_path = 详细文学模板路径
    logger.info(f"Loading detailed literature template from: {template_path}")
    if not template_path.is_file():
        logger.error(f"Detailed literature template file not found: {template_path}")
        return None

    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = yaml.safe_load(f)

        if not template_content or not isinstance(template_content, dict):
            logger.error(f"Detailed literature template file is empty or invalid: {template_path}")
            return None

        logger.info(f"Successfully loaded detailed literature template: {template_path.name}")
        return template_content
    except yaml.YAMLError as e:
        logger.exception(f"Error parsing detailed literature template YAML {template_path}: {e}")
        return None # Indicate error
    except Exception as e:
        logger.exception(f"Unexpected error loading detailed literature template {template_path}: {e}")
        return None # Indicate error

# --- Helper function to find instruction in V2 template --- 
def find_v2_instruction_by_id(template: Dict[str, Any], dimension_id: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Finds the instruction and name for a specific dimension ID in the V2 template structure.
    Returns a tuple: (instruction, parameter_name)
    """
    parts = dimension_id.split('.')
    if not parts:
        return None, None

    current_level_list = template.get('categories', [])
    target_node = None
    current_path_id = ''

    # Traverse the categories/subcategories/parameters based on parts
    for i, part in enumerate(parts):
        found_in_level = False
        current_path_id = part if not current_path_id else f"{current_path_id}.{part}"
        if isinstance(current_level_list, list):
            for item in current_level_list:
                if item.get('id') == part:
                    target_node = item # Update target_node to the currently matched item
                    # Determine the next level to search in: subcategories or parameters
                    next_level_list = item.get('subcategories', item.get('parameters'))
                    if isinstance(next_level_list, list):
                        current_level_list = next_level_list
                    else:
                        # If no subcategories or parameters list, we might be at a leaf or structure error
                        current_level_list = [] # Stop traversal down this path
                    found_in_level = True
                    break # Found item at this level
        if not found_in_level:
            logger.warning(f"Could not find ID part '{part}' (full path tried: '{current_path_id}') in dimension '{dimension_id}' within template structure.")
            return None, None # Path part not found

    # After the loop, target_node should be the node corresponding to the last part of the dimension_id
    if target_node:
        instruction = target_node.get('instruction')
        param_name = target_node.get('name', target_node.get('id')) # Use name, fallback to id

        if instruction:
            logger.debug(f"Found instruction for {dimension_id}")
            return instruction, param_name
        else:
            # Check if it's potentially a non-leaf node (has subcategories or parameters)
            has_children = bool(target_node.get('subcategories') or target_node.get('parameters'))
            if has_children:
                 logger.warning(f"Selected dimension '{dimension_id}' ('{param_name}') seems to be a non-leaf category/subcategory node and lacks a direct instruction.")
            else:
                 logger.warning(f"Found target node '{dimension_id}' ('{param_name}') but it has no 'instruction' field.")
            return None, param_name # Return name even if instruction is missing
    else:
        # This case should ideally not be reached if the loop logic is correct and the ID exists
        logger.error(f"Traversal completed for '{dimension_id}' but target_node is unexpectedly None.")
        return None, None

# --- V2 Prompt Building Logic --- 
def build_detailed_literature_prompt(text: str, selected_dimensions: List[str], template: Dict[str, Any]) -> str:
    """
    Builds the prompt for the V2 literature analysis based on selected dimensions.
    """
    logger.info(f"Building V2 prompt for {len(selected_dimensions)} dimensions.")

    # 1. Get General Instructions (Try metadata first, then root level)
    general_instructions = "请进行详细文学分析。" # Default
    if isinstance(template.get('metadata'), dict) and template['metadata'].get('instructions'):
        general_instructions = template['metadata']['instructions']
    elif template.get('instructions'): # Check root level
        general_instructions = template['instructions']

    # 2. Get Specific Instructions for Selected Dimensions
    specific_instructions_list = []
    found_count = 0
    for dim_id in selected_dimensions:
        instruction, param_name = find_v2_instruction_by_id(template, dim_id)
        if instruction:
            # Format: Use the parameter name for clarity
            specific_instructions_list.append(f"### {param_name} ({dim_id})\n{instruction.strip()}\n")
            found_count += 1
        else:
            logger.warning(f"No instruction found for selected dimension: {dim_id}. It might be a non-leaf node or missing instruction.")
            # Optionally include a note about the missing instruction
            # specific_instructions_list.append(f"### {param_name or dim_id}\n(无法找到具体分析指令，请检查模板或选择。)\n")

    if not specific_instructions_list:
        logger.error("No valid instructions could be extracted for any selected dimension.")
        # Return a generic prompt or raise an error? For now, return a basic prompt.
        return f"""{general_instructions}
请分析以下文本：
--- 文本开始 ---
{text}
--- 文本结束 ---
错误：未能根据所选维度找到任何有效的分析指令。"""

    specific_instructions_str = "\n".join(specific_instructions_list)
    logger.info(f"Extracted instructions for {found_count}/{len(selected_dimensions)} selected dimensions.")

    # 3. Get Output Format Requirements (Optional)
    output_format_desc = "请以清晰、结构化的方式返回分析结果，最好是 JSON 格式，包含所有请求的维度。" # Default
    if isinstance(template.get('output_specification'), dict) and template['output_specification'].get('format'):
         # Simple join if it's a list, otherwise use as string
        output_format_req = template['output_specification']['format']
        if isinstance(output_format_req, list):
            output_format_desc = "输出格式要求: " + ", ".join(output_format_req)
        elif isinstance(output_format_req, str):
            output_format_desc = f"输出格式要求:\n{output_format_req}"
    elif isinstance(template.get('output_format'), str): # Fallback to root output_format
         output_format_desc = f"输出格式要求:\n{template['output_format']}"

    # 4. Assemble the final prompt
    prompt = f"""{general_instructions.strip()}

请基于以下文本内容：
--- 文本开始 ---
{text}
--- 文本结束 ---

请专注于以下选定维度进行深入分析，并严格遵循每个维度的具体分析要求：

{specific_instructions_str}
{output_format_desc}
请确保分析结果的专业性、准确性，并引用文本中的具体例证。"""

    logger.debug(f"Generated V2 Prompt (first 500 chars):\n{prompt[:500]}...")
    return prompt 