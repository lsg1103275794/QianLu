# src/config/api_manager.py
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dotenv import set_key, unset_key, find_dotenv, dotenv_values
import re

# Import necessary functions from factory
from src.providers.factory import standardize_provider_name, get_provider_metadata
# Import the schemas (assuming they are here or accessible)
# If PROVIDER_SCHEMAS is in providers.py, this import needs adjustment
# For now, assume it's accessible or defined locally for get_provider_schema
# from src.api.routes.providers import PROVIDER_SCHEMAS # Example if moved

logger = logging.getLogger(__name__)

# Define PROVIDER_SCHEMAS here or import if defined elsewhere
# Example structure - replace with your actual schema definition source
PROVIDER_SCHEMAS = {} # Placeholder - This needs to be populated from src/api/routes/providers.py

class APIManager:
    """
    API Configuration Manager.
    Primarily responsible for saving configuration settings to the .env file
    and providing configuration schemas for the UI.
    It relies on the provider factory for provider metadata and standardization.
    """
    def __init__(self):
        # Find the .env file path relative to the project root
        try:
            # Assumes this file is src/config/api_manager.py
            _project_root = Path(__file__).resolve().parent.parent.parent
            self.env_file_path = find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=False)
            if not self.env_file_path or not Path(self.env_file_path).exists():
                 # Fallback if not found relative to file, try relative to CWD
                 self.env_file_path = find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=True)
                 if not self.env_file_path or not Path(self.env_file_path).exists():
                     # If still not found, assume it should be in the project root
                     self.env_file_path = str(_project_root / ".env")
                     logger.warning(f".env file not found automatically, assuming path: {self.env_file_path}. File may need creation.")
                 else:
                     logger.info(f"Found .env file relative to CWD: {self.env_file_path}")
            else:
                 logger.info(f"Found .env file: {self.env_file_path}")

        except Exception as e:
            logger.error(f"Error determining .env file path: {e}. Defaulting to './.env'.", exc_info=True)
            self.env_file_path = str(Path("./.env"))


    def save_settings_to_env(self, env_vars_to_update: Dict[str, Optional[str]]) -> Tuple[bool, str]:
        """
        Saves or removes environment variables in the .env file.

        Args:
            env_vars_to_update: A dictionary where keys are environment variable names
                                and values are the new values (as strings).
                                If a value is None, the key will be removed from the .env file.

        Returns:
            A tuple (success: bool, message: str).
        """
        logger.info(f"Attempting to save/update {len(env_vars_to_update)} variable(s) in {self.env_file_path}")
        logger.debug(f"Variables to update: {env_vars_to_update}")
        try:
            # Ensure the .env file exists, create if not
            env_path = Path(self.env_file_path)
            if not env_path.exists():
                try:
                    env_path.touch()
                    logger.info(f"Created non-existent .env file at: {self.env_file_path}")
                except OSError as e:
                    logger.error(f"Failed to create .env file at {self.env_file_path}: {e}")
                    return False, f"无法创建 .env 文件: {e}"

            # Use the helper to perform the save operation
            self._save_env_file(env_vars_to_update)

            logger.info(f"Successfully updated variables in {self.env_file_path}")
            return True, ".env 文件已成功更新。"
        except Exception as e:
            logger.error(f"Failed to save settings to .env file ({self.env_file_path}): {e}", exc_info=True)
            return False, f"保存设置到 .env 文件时出错: {e}"

    def _save_env_file(self, env_vars_to_update: Dict[str, Optional[str]]):
        """
        Internal helper to modify the .env file using python-dotenv.

        Args:
            env_vars_to_update: Dictionary of keys to update/remove.
                                Value None means remove the key.
        """
        if not self.env_file_path:
            raise ValueError("无法确定 .env 文件路径，无法保存。")

        for key, value in env_vars_to_update.items():
            # Basic validation or sanitization of key/value if needed
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", key):
                logger.warning(f"Skipping invalid environment variable key: '{key}'")
                continue

            try:
                if value is None:
                    # Remove the key if value is None
                    unset_key(self.env_file_path, key, verbose=True)
                    logger.debug(f"Removed key '{key}' from {self.env_file_path}")
                else:
                    # Set or update the key-value pair
                    # Ensure value is a string, quote if necessary (set_key handles basic quoting)
                    str_value = str(value)
                    # Add quotes if value contains spaces or special characters?
                    # set_key should handle basic cases. Add logic here if more complex quoting is needed.
                    # if ' ' in str_value or '#' in str_value:
                    #     str_value = f'"{str_value}"' # Simple quoting
                    set_key(self.env_file_path, key, str_value, quote_mode="always", verbose=True) # Use always quote for consistency
                    logger.debug(f"Set key '{key}' to '{str_value}' in {self.env_file_path}")
            except Exception as e:
                 # Log error for specific key but continue with others
                 logger.error(f"Error setting/unsetting key '{key}' in {self.env_file_path}: {e}", exc_info=True)
                 # Optionally raise an exception here if one failure should stop the whole process


    def get_provider_schema(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the configuration schema for a given provider.
        This schema is used by the frontend to generate configuration forms.

        Args:
            provider_name: The name or alias of the provider.

        Returns:
            A dictionary representing the provider's configuration schema (based on
            PROVIDER_SCHEMAS), or None if the provider or schema is not found.
        """
        global PROVIDER_SCHEMAS # Access the schema definition
        if not PROVIDER_SCHEMAS:
             logger.warning("PROVIDER_SCHEMAS is not populated. Cannot retrieve schema.")
             # Attempt to import dynamically if needed - This indicates a dependency issue
             try:
                  from src.api.routes.providers import PROVIDER_SCHEMAS as imported_schemas
                  PROVIDER_SCHEMAS = imported_schemas
                  logger.info("Dynamically loaded PROVIDER_SCHEMAS from routes.providers")
             except ImportError:
                  logger.error("Failed to dynamically import PROVIDER_SCHEMAS from src.api.routes.providers.")
                  return None
             except AttributeError:
                  logger.error("PROVIDER_SCHEMAS not found in src.api.routes.providers.")
                  return None


        try:
            standard_name = standardize_provider_name(provider_name)
            logger.debug(f"Retrieving schema for standardized provider name: {standard_name}")

            schema = PROVIDER_SCHEMAS.get(standard_name)
            if schema:
                logger.debug(f"Found schema for {standard_name}.")
                # Return a copy to prevent modification of the original schema
                return schema.copy()
            else:
                logger.warning(f"No schema found in PROVIDER_SCHEMAS for provider: {standard_name}")
                return None
        except ValueError as e:
            # standardize_provider_name raises ValueError if provider is unknown
            logger.warning(f"Cannot get schema for unknown provider '{provider_name}': {e}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving schema for provider '{provider_name}': {e}", exc_info=True)
            return None

    def get_config(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """获取指定 API 提供商的完整配置（从.env文件直接读取）。"""
        try:
            from src.providers.factory import get_provider_metadata, standardize_provider_name
            
            # 获取标准化的提供商名称
            try:
                standard_name = standardize_provider_name(provider_name)
            except ValueError as e:
                logger.error(f"无法标准化提供商名称 '{provider_name}': {e}")
                return None
                
            # 获取提供商元数据以确定环境变量前缀
            provider_meta = get_provider_metadata(standard_name)
            if not provider_meta:
                logger.error(f"找不到提供商 '{provider_name}' 的元数据。")
                return None
                
            # 从元数据中获取环境变量前缀
            env_prefix = provider_meta.get('env_prefix')
            if not env_prefix:
                logger.error(f"提供商 '{provider_name}' 的元数据中缺少 env_prefix。")
                return None
                
            # 从.env文件读取配置
            env_values = dotenv_values(self.env_file_path)
            if not env_values:
                logger.warning(f"在 {self.env_file_path} 中找不到任何环境变量。")
                return None
                
            # 构建配置字典
            config = {
                "standard_name": standard_name,
                "display_name": provider_meta.get('display_name', standard_name),
                "enabled": True,  # 在这个方案中，我们假设如果存在配置文件，则提供商已启用
                "credentials": {},
                "env_prefix": env_prefix
            }
            
            # 添加必要的环境变量值
            config["endpoint"] = env_values.get(f"{env_prefix}ENDPOINT")
            config["default_model"] = env_values.get(f"{env_prefix}DEFAULT_MODEL")
            
            # 收集凭据相关的环境变量
            credential_keys = [
                "API_KEY", "API_SECRET", "ACCESS_KEY", "SECRET_KEY", 
                "APP_ID", "APP_SECRET", "AUTH_TOKEN"
            ]
            for key in credential_keys:
                env_key = f"{env_prefix}{key}"
                if env_key in env_values and env_values[env_key]:
                    config["credentials"][key.lower()] = env_values[env_key]
            
            # 如果没有找到任何凭据，将credentials设置为None
            if not config["credentials"]:
                config["credentials"] = None
                
            # 确定需要的键（基于提供商）
            requires_keys = []
            if standard_name == "openai":
                requires_keys = ["api_key"]
            elif standard_name == "azure_openai":
                requires_keys = ["api_key"]
            elif standard_name == "ollama_local":
                requires_keys = []  # Ollama可能不需要API密钥
            elif standard_name == "open_router":
                requires_keys = ["api_key"]
            elif standard_name == "gemini":
                requires_keys = ["api_key"]
            elif standard_name == "anthropic":
                requires_keys = ["api_key"]
            # 可以根据需要添加更多提供商
            
            config["requires_keys"] = requires_keys
            
            return config
            
        except Exception as e:
            logger.error(f"获取提供商配置失败 '{provider_name}': {e}", exc_info=True)
            return None

    def is_provider_configured(self, provider_name: str) -> Tuple[bool, str]:
        """
        检查指定的 API 提供商是否已在 .env 文件中正确配置。
        
        Args:
            provider_name: 提供商的标准名称或别名。
            
        Returns:
            Tuple[bool, str]: (是否已配置, 描述信息)
        """
        try:
            # 1. 标准化名称并获取元数据
            standard_name = standardize_provider_name(provider_name)
            metadata = get_provider_metadata(standard_name)
            
            if not metadata:
                return False, f"找不到提供商 '{provider_name}' 的元数据。"
                
            env_prefix = metadata.get('env_prefix')
            if not env_prefix:
                return False, f"提供商 '{provider_name}' 的元数据中缺少 env_prefix。"
            
            # 2. 确定需要检查的环境变量
            # 基础检查: 通常需要 API_KEY 或 ENDPOINT (Ollama 除外)
            required_vars = []
            if standard_name == "ollama_local":
                required_vars.append(f"{env_prefix}ENDPOINT")
            else:
                # 对大多数其他提供商，API_KEY 是必须的
                required_vars.append(f"{env_prefix}API_KEY")
                # 某些提供商可能还需要ENDPOINT
                # if standard_name in ["azure_openai", ...]:
                #     required_vars.append(f"{env_prefix}ENDPOINT")
            
            # 添加其他可能的必须字段 (可以从 schema 获取)
            # schema = self.get_provider_schema(standard_name)
            # if schema:
            #     for item in schema:
            #         if item.get('required') and item.get('env_var'):
            #             if item['env_var'] not in required_vars:
            #                 required_vars.append(item['env_var'])
                            
            logger.debug(f"检查提供商 '{standard_name}' 的配置，需要变量: {required_vars}")

            # 3. 读取 .env 文件
            env_values = dotenv_values(self.env_file_path)
            if not env_values:
                logger.warning(f"无法读取或找不到 .env 文件: {self.env_file_path}")
                return False, f"未找到或无法读取 .env 文件。"
            
            # 4. 检查必需的变量是否存在且非空
            missing_vars = []
            empty_vars = []
            for var in required_vars:
                if var not in env_values:
                    missing_vars.append(var)
                elif not env_values[var]: # 值为空字符串也被认为未配置
                    empty_vars.append(var)
            
            if missing_vars:
                msg = f"提供商 '{standard_name}' 未配置，缺少环境变量: {', '.join(missing_vars)}。"
                logger.info(msg)
                return False, msg
            elif empty_vars:
                msg = f"提供商 '{standard_name}' 配置不完整，环境变量值为空: {', '.join(empty_vars)}。"
                logger.info(msg)
                return False, msg
            else:
                msg = f"提供商 '{standard_name}' 已配置。"
                logger.info(msg)
                return True, msg
                
        except ValueError as e:
            # standardize_provider_name or get_provider_metadata failed
            return False, f"检查提供商 '{provider_name}' 配置时出错: {e}"
        except Exception as e:
            logger.error(f"检查提供商 '{provider_name}' 配置时发生意外错误: {e}", exc_info=True)
            return False, f"检查配置时发生内部错误: {e}"

# Instantiate the manager for potential use elsewhere (e.g., routes)
# Note: It's now much more lightweight as it doesn't load/cache configs.
api_manager = APIManager()

logger.info("APIManager (主配置源: .env) 初始化完成。") 