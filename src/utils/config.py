"""
配置管理器模块，提供配置文件和系统设置的管理
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

# --- 基础路径配置 ---
# Assuming this config file is at src/utils/config.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent # Get project root (up 3 levels from src/utils)
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True) # Ensure the directory exists

# --- 配置日志 ---
logger = logging.getLogger(__name__)

class ConfigManager:
    """
    配置管理器类 - 简化版：仅用于加载和保存 configs.json 中的显示名称。
    核心配置由 APIManager 通过 .env 管理。
    """
    def __init__(self):
        self.config_path = Path(__file__).resolve().parents[2] / "config" / "configs.json"
        self.display_names = {} # 只存储显示名称
        self.load_display_names()
    
    def load_display_names(self):
        """仅从 configs.json 加载提供商的显示名称。"""
        self.display_names = {}
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                providers_data = data.get("providers", {})
                if isinstance(providers_data, dict):
                    from src.providers.factory import APIHandlerFactory # 延迟导入
                    for provider_raw, config in providers_data.items():
                        if isinstance(config, dict) and "display_name" in config:
                            provider_name = APIHandlerFactory.standardize_provider_name(provider_raw)
                            self.display_names[provider_name] = config["display_name"]
                logger.info(f"从 {self.config_path} 加载了 {len(self.display_names)} 个显示名称。")
            else:
                logger.warning(f"JSON 配置文件 {self.config_path} 不存在，无法加载显示名称。")
        except Exception as e:
            logger.error(f"从 {self.config_path} 加载显示名称时出错: {e}", exc_info=True)

    def get_display_name(self, provider_name: str) -> Optional[str]:
        """获取指定提供商的显示名称。"""
        from src.providers.factory import APIHandlerFactory # 延迟导入
        standard_name = APIHandlerFactory.standardize_provider_name(provider_name)
        return self.display_names.get(standard_name)

    def save_display_names(self, provider_configs: Dict[str, Dict[str, Any]]) -> bool:
        """根据传入的配置更新并保存显示名称到 configs.json。"""
        updated = False
        from src.providers.factory import APIHandlerFactory # 延迟导入
        for provider_raw, config in provider_configs.items():
            if isinstance(config, dict) and "display_name" in config:
                 provider_name = APIHandlerFactory.standardize_provider_name(provider_raw)
                 if self.display_names.get(provider_name) != config["display_name"]:
                      self.display_names[provider_name] = config["display_name"]
                      updated = True
        
        if updated:
            logger.info("检测到显示名称变更，正在保存到 configs.json...")
            providers_data_to_save = {}
            for name, display_name in self.display_names.items():
                 providers_data_to_save[name] = {"display_name": display_name}
            data_to_save = {"providers": providers_data_to_save}
            try:
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, indent=4, ensure_ascii=False)
                logger.info(f"显示名称已保存到 {self.config_path}")
                return True
            except Exception as e:
                logger.error(f"保存显示名称到 {self.config_path} 时出错: {e}")
                return False
        else:
             logger.debug("显示名称未发生变化，无需保存 JSON。")
             return True # 没有变化也算成功

    # 移除所有旧的获取/保存核心配置的方法
    # def load_configs(self): ...
    # def _init_default_configs(self): ...
    # def save_configs(self): ... (现在由 save_display_names 替代)
    # def get_provider_settings(self) -> Dict[str, Any]: ...
    # def get_global_settings(self) -> Dict[str, Any]: ...
    # def get_templates(self) -> List[Dict[str, Any]]: ...
    # def update_default_provider(self, provider: str) -> bool: ...
    # def save_global_settings(self, settings: Dict[str, Any]) -> bool: ...
    # def save_provider_settings(self, settings: Dict[str, Dict[str, Any]]) -> bool: ...
    # def save_single_provider_settings(self, provider: str, config: Dict[str, Any]) -> bool: ...

# 注意：全局实例不再需要，因为路由直接使用 APIManager
# 配置管理器 = ConfigManager() 

# --- .env 文件操作 ---
from dotenv import dotenv_values, set_key, find_dotenv

def update_dotenv_vars(vars_to_update: Dict[str, str]) -> bool:
    """
    更新项目根目录下的 .env 文件中的变量。
    如果 .env 文件不存在，则会尝试创建。

    Args:
        vars_to_update: 一个包含要更新或添加的环境变量键值对的字典。

    Returns:
        True 如果操作成功，False 如果出现错误。
    """
    try:
        dotenv_path = find_dotenv(raise_error_if_not_found=False, usecwd=True)
        if not dotenv_path:
            # 如果找不到 .env 文件，尝试在项目根目录创建
            project_root_env = PROJECT_ROOT / ".env"
            project_root_env.touch(exist_ok=True) # 创建空文件
            dotenv_path = str(project_root_env)
            logger.info(f".env 文件未找到，已在 {dotenv_path} 创建。")
        
        # 加载现有变量（如果文件存在）
        current_values = dotenv_values(dotenv_path)
        
        # 更新或添加变量
        updated = False
        for key, value in vars_to_update.items():
            # python-dotenv 的 set_key 会处理添加或修改
            # 确保 key 是字符串，value 也转为字符串
            str_value = str(value) if value is not None else ''
            set_key(dotenv_path, key, str_value, quote_mode='always')
            # 检查值是否真的改变了（注意类型可能不同）
            if key not in current_values or str(current_values[key]) != str_value:
                 updated = True
                 logger.debug(f"设置环境变量: {key}={str_value}")

        if updated:
            logger.info(f"成功更新了 {len(vars_to_update)} 个环境变量到 {dotenv_path}")
        else:
            logger.info(".env 文件中的值未发生变化。")
            
        return True # set_key 内部会处理保存

    except Exception as e:
        logger.error(f"更新 .env 文件 ({dotenv_path}) 时出错: {e}", exc_info=True)
        return False 