# ... (imports as before) ...
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import os
import sys
import socket
import logging

from src.utils.logger import logger # Import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROMPT_TEMPLATE_DIR = PROJECT_ROOT / "config" / "prompt_templates"

def load_prompt_template(template_name: str) -> Optional[Dict[str, Any]]:
    """
    从 YAML 文件加载提示模板的完整内容（包括元数据）。
    并进行基本结构校验。
    """
    template_path = PROMPT_TEMPLATE_DIR / f"{template_name}.yaml"
    if not template_path.exists():
        logger.error(f"Prompt template file not found: {template_path}")
        return None
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            if not isinstance(data, dict):
                logger.error(f"Prompt template '{template_name}.yaml' is not a valid dictionary.")
                return None

            # --- 基本结构校验 ---
            if "full_prompt_template" not in data or not isinstance(data["full_prompt_template"], str):
                 logger.error(f"Prompt template '{template_name}.yaml' is missing required key 'full_prompt_template' or it's not a string.")
                 return None
            if "meta" not in data or not isinstance(data.get("meta"), dict):
                 logger.warning(f"Prompt template '{template_name}.yaml' is missing 'meta' section or it's not a dict. Metadata will be incomplete.")
                 data["meta"] = {} # Add empty meta if missing

            logger.debug(f"Successfully loaded prompt template: {template_name}")
            return data
    except (yaml.YAMLError, IOError) as e:
        logger.error(f"Failed to load or parse prompt template {template_name}: {e}")
        return None
    except Exception as e:
         logger.error(f"Unexpected error loading prompt template {template_name}: {e}", exc_info=True)
         return None


def get_available_prompts() -> List[Dict[str, Any]]:
     """扫描模板目录，返回所有有效模板的元数据列表。"""
     available = []
     if not PROMPT_TEMPLATE_DIR.is_dir():
          logger.error(f"Prompt template directory not found or not a directory: {PROMPT_TEMPLATE_DIR}")
          return []

     for filepath in PROMPT_TEMPLATE_DIR.glob("*.yaml"):
          template_name = filepath.stem
          template_data = load_prompt_template(template_name)
          if template_data and isinstance(template_data.get("meta"), dict): # 确保加载成功且有 meta
               meta = template_data["meta"]
               available.append({
                   "name": template_name,
                   "description": meta.get("description", "No description available."),
                   "version": meta.get("version", "N/A"),
                   "tags": meta.get("tags", []),
                   # 可以添加其他需要的信息
               })
          elif template_data: # 加载成功但 meta 信息不全或无效
               available.append({"name": template_name, "description": "Metadata missing or invalid."})
          # 如果 load_prompt_template 返回 None (加载失败或校验失败)，则不添加到列表

     logger.info(f"Found {len(available)} available prompt templates.")
     return available


def format_prompt(template_name: str, **kwargs) -> Optional[str]:
    """根据模板名称和输入参数格式化最终的提示。"""
    template_data = load_prompt_template(template_name)
    if template_data is None:
        return None # 模板加载或校验失败

    base_template = template_data["full_prompt_template"] # 已在 load 时校验存在

    # 准备填充字典：合并模板自身字段（除了 meta）和传入的 kwargs
    format_args = {k: v for k, v in template_data.items() if k != "meta"}
    format_args.update(kwargs) # 调用时传入的 kwargs 优先级更高

    try:
        # 使用 str.format 进行替换
        formatted = base_template.format(**format_args)
        # 可以在这里添加一个检查，确保模板中定义的所有 variables 都被填充了
        required_vars = template_data.get("meta", {}).get("variables", [])
        missing_vars = [var for var in required_vars if var not in format_args]
        if missing_vars:
             logger.error(f"Formatting prompt '{template_name}': Missing required variables defined in meta: {missing_vars}. Available keys: {list(format_args.keys())}")
             # return None # 可以选择因缺少变量而失败
             # 或者只记录错误，返回部分格式化的模板
             # formatted = base_template # 或者尝试用空字符串填充？

        logger.debug(f"Successfully formatted prompt '{template_name}'.")
        return formatted
    except KeyError as e:
        # 如果模板字符串引用了 format_args 中不存在的 key
        logger.error(f"Formatting prompt '{template_name}' failed: Missing key {e}. Available keys: {list(format_args.keys())}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error formatting prompt '{template_name}': {e}", exc_info=True)
        return None

def ensure_directories() -> None:
    """确保必要的目录结构存在"""
    dirs = [
        "output",
        "cache",
        "resources",
        "resources/dictionaries",
        "input",
        "data/style_analysis_cache"
    ]
    
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
    
    # 创建配置目录，如果不存在
    config_dir = Path("src/config")
    if not config_dir.exists():
        config_dir.mkdir(parents=True)

def find_available_port(start_port: int, end_port: int) -> Optional[int]:
    """查找指定范围内的可用端口"""
    for port in range(start_port, end_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                continue
    return None

def check_dependencies(logger: logging.Logger) -> bool:
    """检查所需的依赖是否已安装"""
    required_dependencies = [
        "streamlit",
        "python-dotenv",
        "requests",
        "pydantic",
        "loguru",
        "jieba"
    ]
    
    # 定义依赖映射，确保导入的模块名称正确
    dep_mapping = {
        "python-dotenv": "dotenv",
        "pydantic": "pydantic",
        "loguru": "loguru"
    }
    
    missing_required = []
    
    for dep in required_dependencies:
        module_name = dep_mapping.get(dep, dep.replace("-", "_").split(".")[0])
        try:
            __import__(module_name)
        except ImportError:
            missing_required.append(dep)
    
    if missing_required:
        logger.error(f"缺少必需的依赖: {', '.join(missing_required)}")
        logger.error(f"请执行: pip install {' '.join(missing_required)}")
        return False
    
    return True

def validate_environment(logger: logging.Logger) -> Tuple[bool, List[str], List[str]]:
    """验证环境配置，并返回详细结果。"""
    from src.utils.config_validator import ConfigValidator
    
    validator = ConfigValidator()
    
    # validate_all 返回 (valid, errors, warnings)
    valid, errors, warnings = validator.validate_all()
    
    # Log errors and warnings here as before
    if not valid or errors:
        logger.error(f"环境配置验证失败，发现 {len(errors)} 个错误")
        for error in errors:
            logger.error(f"配置错误: {error}")
        # Don't return False here anymore
    
    if warnings:
        logger.warning(f"环境配置验证通过，但有 {len(warnings)} 个警告") # Log warnings even if valid
        for warning in warnings:
            logger.warning(f"配置警告: {warning}")
    
    # Return the original tuple from validator.validate_all()
    return valid, errors, warnings 

def get_supported_file_types() -> List[str]:
    """获取支持的文件类型列表"""
    return [".txt", ".pdf", ".docx", ".epub", ".md"]

def format_file_size(size_in_bytes: int) -> str:
    """格式化文件大小显示"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.2f} TB"

def safe_get_config(config: Dict[str, Any], key: str, default: Any = None) -> Any:
    """安全地获取配置值"""
    try:
        return config.get(key, default)
    except Exception:
        return default

# --- 测试代码 ---
if __name__ == '__main__':
     import pprint # Import pprint only for testing block
     # ... (之前的 helpers 测试) ...
     print("\n--- 测试 Prompt (细化版) ---")
     available = get_available_prompts()
     print("Available prompts:")
     pprint.pprint(available)

     if available:
          first_prompt_name = available[0]['name']
          print(f"\nFormatting prompt '{first_prompt_name}'...")
          formatted = format_prompt(first_prompt_name, input_text="This is the sample input text for the prompt.")
          if formatted:
               print("Formatted Prompt Preview:\n", formatted[:400], "...")
          else:
               print("Formatting failed.")

          # 测试缺少变量
          print("\nFormatting prompt without required 'input_text'...")
          formatted_missing = format_prompt(first_prompt_name) # 不传入 input_text
          # format_prompt 现在应该会记录错误（如果 meta 中定义了 variables）
          # 并且可能返回 None (如果选择失败) 或部分格式化的模板
          if formatted_missing: print("Formatted (maybe partially):\n", formatted_missing[:200], "...")
          else: print("Formatting failed as expected due to missing variable.")