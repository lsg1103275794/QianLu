"""
API handler factory implementation using external metadata.
"""
import logging
import importlib
import os
import dotenv
import json
from typing import Dict, Type, Any, Optional, List, TypedDict
from src.utils.logging import logger as 日志记录器
from src.providers.base import BaseAPIHandler
from pathlib import Path
from dotenv import dotenv_values, find_dotenv

# --- Provider Metadata Structure Definition ---
class ProviderMetadata(TypedDict):
    """Defines the expected structure for each entry in providers_meta.json."""
    standard_name: str         # Internal standard identifier (e.g., "silicon_flow")
    display_name: str          # Name shown in the UI (e.g., "Silicon Flow")
    handler_module_path: str   # Python path to the handler module (e.g., "src.providers.handlers.silicon_flow")
    handler_class_name: str    # Class name of the handler (e.g., "SiliconFlowHandler")
    aliases: List[str]         # List of alternative names/aliases (e.g., ["silicon", "siliconflow"])
    env_prefix: str            # Prefix for environment variables in .env (e.g., "SILICONFLOW_")

# --- Module Level State ---
# These dictionaries store the dynamically loaded information.
_handlers: Dict[str, Type[BaseAPIHandler]] = {}              # Maps standard_name to Handler Class
_provider_aliases: Dict[str, str] = {}                       # Maps normalized alias to standard_name
_provider_metadata_map: Dict[str, ProviderMetadata] = {}     # Maps standard_name to its full metadata dict
_initialized = False                                         # Tracks if initialization has run
_project_root: Optional[Path] = None

# --- Configuration ---
# Define the path to the metadata file. Assumes this script is in src/providers/
# and the config directory is at the project root (sibling to src/).
try:
    _CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    _PROJECT_ROOT = os.path.abspath(os.path.join(_CURRENT_DIR, '..', '..'))
    CONFIG_DIR = os.path.join(_PROJECT_ROOT, 'config')
    METADATA_FILE = os.path.join(CONFIG_DIR, 'providers_meta.json')
except NameError:
    # Fallback if __file__ is not defined (e.g., in some execution environments)
    日志记录器.warning("Could not determine project root using __file__. Assuming current working directory.")
    _PROJECT_ROOT = os.getcwd()
    CONFIG_DIR = os.path.join(_PROJECT_ROOT, 'config')
    METADATA_FILE = os.path.join(CONFIG_DIR, 'providers_meta.json')

日志记录器.debug(f"Project root detected as: {_PROJECT_ROOT}")
日志记录器.debug(f"Metadata file path set to: {METADATA_FILE}")


class APIHandlerFactory:
    """
    Factory class for creating API handlers.
    Relies on metadata loaded from an external file (providers_meta.json)
    and configuration read directly from the .env file at runtime.
    Does not cache handler instances to ensure fresh config on each request.
    """

    # Use module-level state variables for storing loaded data
    _handlers = _handlers
    _provider_aliases = _provider_aliases
    _provider_metadata_map = _provider_metadata_map

    @classmethod
    def standardize_provider_name(cls, provider: str) -> str:
        """
        Standardizes the input provider name by converting to lowercase,
        replacing hyphens with underscores, and resolving aliases using
        the loaded metadata.
        
        Args:
            provider: The provider name input by the user or system.
            
        Returns:
            The standardized provider name corresponding to a registered handler.

        Raises:
            ValueError: If the provider name is empty or cannot be resolved
                        to a known standard name or alias after initialization.
        """
        if not provider:
            日志记录器.error("提供商名称不能为空。")
            raise ValueError("提供商名称不能为空。")
            
        # Normalize: lowercase, replace spaces and hyphens
        normalized = provider.lower().replace(" ", "").replace("-", "_")
        
        # Ensure handlers are initialized to populate aliases and handlers map
        if not _initialized:
            initialize_handlers()

        # 1. Check if the normalized name is a registered alias
        if normalized in cls._provider_aliases:
            standard_name = cls._provider_aliases[normalized]
            日志记录器.debug(f"提供商名称 '{provider}' (标准化: '{normalized}') 通过别名映射到标准名称 '{standard_name}'")
            return standard_name
            
        # 2. Check if the normalized name is already a known standard name
        if normalized in cls._handlers: # Check against keys of the registered handlers map
            日志记录器.debug(f"提供商名称 '{provider}' (标准化: '{normalized}') 已是标准名称。")
            return normalized
            
        # 3. If neither, it's an unknown provider
        日志记录器.error(f"未知的提供商: '{provider}' (标准化: '{normalized}')。")
        available_handlers = list(cls._handlers.keys())
        available_aliases = list(cls._provider_aliases.keys())
        日志记录器.info(f"可用标准提供商名称: {available_handlers}")
        日志记录器.info(f"可用别名: {available_aliases}")
        raise ValueError(f"未知的提供商: '{provider}'。请检查可用的提供商和别名。")

    @classmethod
    def get_handler(cls, provider: str) -> BaseAPIHandler:
        """
        Creates and returns a *new* API handler instance for the specified provider.
        Reads configuration from the provider's specific JSON config file (if defined)
        and merges it with values from the .env file (JSON takes precedence).
        
        Args:
            provider: The name of the API provider (will be standardized).
            
        Returns:
            A newly created instance of the appropriate API handler subclass.

        Raises:
            RuntimeError: If handler initialization failed previously.
            ValueError: If the provider name is invalid, metadata is missing,
                        config loading fails, or handler instantiation fails.
        """
        # Ensure factory is initialized (idempotent check)
        if not _initialized:
            日志记录器.warning("在显式初始化之前尝试获取处理器。正在初始化。")
            initialize_handlers()
            if not _initialized:
                raise RuntimeError("处理器初始化失败。无法获取处理器。")

        # Get the standard name (handles aliases)
        standard_provider = cls.standardize_provider_name(provider)
        
        # Retrieve the Handler class and metadata
        if standard_provider not in cls._handlers:
            日志记录器.critical(f"内部错误: 对于已验证的标准提供商 {standard_provider} 未找到处理器类")
            raise ValueError(f"内部错误: 对于已知提供商 {standard_provider} 未找到处理器类")

        handler_class = cls._handlers[standard_provider]
        provider_meta = cls._provider_metadata_map.get(standard_provider)

        if not provider_meta:
            日志记录器.error(f"严重错误: 找到了处理器类但未找到 '{standard_provider}' 的元数据。")
            return None # Should not happen if initialization is correct

        # --- 恢复：移除优化，改回在循环内加载 .env --- 
        # dotenv_path = find_dotenv(raise_error_if_not_found=False)
        # all_env_vars = {**dotenv_values(dotenv_path), **os.environ} 
        # 日志记录器.debug(f"get_handler: 已加载 .env 文件 ({dotenv_path}) 和系统环境变量。")
        # -----------------------------------------

        # --- 简化配置加载逻辑：只从环境变量加载 --- 
        config = {}
        env_prefix = provider_meta.get("env_prefix")
        
        if env_prefix:
            日志记录器.debug(f"正在为提供商 '{standard_provider}' 加载前缀为 '{env_prefix}' 的环境变量...")
            # --- 恢复：在需要时加载 --- 
            dotenv_path = find_dotenv(raise_error_if_not_found=False) 
            all_env_vars = {**dotenv_values(dotenv_path), **os.environ} 
            # ------------------------

            prefix_len = len(env_prefix)
            for key, value in all_env_vars.items(): # 使用新加载的 all_env_vars
                if key.startswith(env_prefix):
                    config_key = key 
                    processed_value = value 
                    if value is not None:
                        if value.lower() in ['true', 'false']:
                            processed_value = value.lower() == 'true'
                        else:
                            try:
                                # 尝试转换为 int 或 float
                                if '.' in value:
                                    processed_value = float(value)
                                else:
                                    processed_value = int(value)
                            except ValueError:
                                pass # 保持为字符串
                    
                    config[config_key] = processed_value
                    # 日志记录器.debug(f"  加载的环境变量: {config_key} = {processed_value}")
            日志记录器.debug(f"为 '{standard_provider}' 加载的最终配置键 (来自环境变量): {list(config.keys())}")
        else:
            日志记录器.warning(f"提供商 '{standard_provider}' 在元数据中没有定义 'env_prefix'，将不会从环境变量加载配置。")

        # --- 直接将扁平的配置字典传递给 Handler ---
        try:
            # 添加 provider_name 到配置中，方便 Handler 内部使用
            config['provider_name'] = standard_provider 
            handler_instance = handler_class(config)
            日志记录器.info(f"成功创建提供商 '{standard_provider}' 的处理器实例。")
            return handler_instance
        except Exception as e:
            日志记录器.exception(f"初始化提供商 '{standard_provider}' 的处理器时出错: {e}")
            return None

    # Note: register_handler and register_alias class methods are removed.
    # Registration is now handled centrally within initialize_handlers based on the metadata file.


# --- Initialization Function ---
def initialize_handlers():
    """
    Initializes the API handler factory by reading the provider metadata file.
    This function populates the internal dictionaries (_handlers, _provider_aliases,
    _provider_metadata_map) and should be called once at application startup
    or before the first call to get_handler. It is designed to be idempotent.
    """
    global _initialized, _handlers, _provider_aliases, _provider_metadata_map, _project_root
    
    # Prevent redundant execution
    if _initialized:
        日志记录器.debug("处理器工厂已初始化。")
        return
        
    日志记录器.info(f"正在从元数据文件初始化 API 处理器: {METADATA_FILE}")
    # Clear existing state in case of re-initialization attempt (though ideally only called once)
    _handlers.clear()
    _provider_aliases.clear()
    _provider_metadata_map.clear()
    _project_root = Path(_PROJECT_ROOT)

    try:
        # 1. Check if metadata file exists
        if not os.path.exists(METADATA_FILE):
            日志记录器.error(f"提供商元数据文件未找到: {METADATA_FILE}。无法初始化处理器。")
            # Mark as failed and exit initialization
            _initialized = False
            raise FileNotFoundError(f"提供商元数据文件未找到: {METADATA_FILE}")  # Raise to signal critical failure
            
        # 检查文件权限
        try:
            # 获取文件权限
            file_permissions = oct(os.stat(METADATA_FILE).st_mode)[-3:]
            日志记录器.info(f"元数据文件权限: {file_permissions}, 路径: {METADATA_FILE}")
            
            # 尝试读取文件前几个字符进行测试
            with open(METADATA_FILE, 'r', encoding='utf-8') as test_f:
                test_content = test_f.read(20)
                日志记录器.info(f"元数据文件前20个字符: {test_content}")
        except Exception as perm_err:
            日志记录器.error(f"检查元数据文件权限时出错: {perm_err}")
            _initialized = False
            raise ValueError(f"无法读取元数据文件 (权限问题): {perm_err}")

        # 2. Read and parse the JSON file
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            try:
                # Parse JSON - expecting a list of provider metadata dictionaries
                providers_metadata: List[ProviderMetadata] = json.load(f)
                日志记录器.debug(f"成功解析 {METADATA_FILE} 中的 JSON 数据")
            except json.JSONDecodeError as json_err:
                日志记录器.error(f"解析元数据文件 {METADATA_FILE} 中的 JSON 时出错: {json_err}")
                _initialized = False
                raise ValueError(f"元数据文件 {METADATA_FILE} 中的 JSON 格式无效") from json_err

        # 3. Validate the overall structure (should be a list)
        if not isinstance(providers_metadata, list):
            # 记录错误并设置初始化标志为False
            error_msg = f"元数据文件 {METADATA_FILE} 格式无效: 顶层应为 JSON 列表 (数组)，但找到类型 {type(providers_metadata)}"
            日志记录器.error(error_msg)
            _initialized = False
            raise ValueError(f"元数据文件 {METADATA_FILE} 格式无效: 顶层应为 JSON 列表")

        # 4. Process each provider's metadata entry
        registration_count = 0
        for meta in providers_metadata:
            if not isinstance(meta, dict):
                日志记录器.warning(f"跳过元数据文件中的无效条目: 预期是字典，得到 {type(meta)}。条目: {meta}")
                continue # Skip this entry

            try:
                # --- Extract and Validate Metadata Keys ---
                # Use .get() with fallback for robustness, or rely on TypedDict structure
                standard_name = meta.get('standard_name')
                module_path = meta.get('handler_module_path')
                class_name = meta.get('handler_class_name')
                aliases = meta.get('aliases', []) # Default to empty list if missing
                env_prefix = meta.get('env_prefix')
                display_name = meta.get('display_name', standard_name) # Use standard_name if display_name missing

                # Basic validation for required fields
                if not all([standard_name, module_path, class_name, env_prefix]):
                    missing = [k for k, v in {'standard_name': standard_name, 'handler_module_path': module_path, 'handler_class_name': class_name, 'env_prefix': env_prefix}.items() if not v]
                    日志记录器.error(f"由于缺少必需的键 {missing}，跳过元数据条目: {meta}")
                    continue

                if not isinstance(aliases, list):
                    日志记录器.warning(f"'{standard_name}' 的 'aliases' 格式无效（预期为列表，得到 {type(aliases)}）。当作空列表处理。条目: {meta}")
                    aliases = []

                # --- Dynamically Import Handler Class ---
                try:
                    module = importlib.import_module(module_path)
                    handler_class = getattr(module, class_name)
                except ImportError as import_err:
                    日志记录器.error(f"无法为提供商 '{standard_name}' 导入模块 '{module_path}'。错误: {import_err}。跳过注册。")
                    continue # Skip this provider
                except AttributeError:
                    日志记录器.error(f"在模块 '{module_path}' 中未找到提供商 '{standard_name}' 的处理器类 '{class_name}'。跳过注册。")
                    continue # Skip this provider

                # --- Validate Handler Class ---
                if not issubclass(handler_class, BaseAPIHandler):
                    日志记录器.warning(f"提供商 '{standard_name}' 的处理器类 '{class_name}' 不继承自 BaseAPIHandler。跳过注册。")
                    continue # Skip this provider

                # --- Register Handler, Metadata, and Aliases ---
                # Check for standard name conflicts
                if standard_name in _handlers:
                    日志记录器.warning(f"在元数据中发现重复的 standard_name '{standard_name}'。覆盖之前的注册。")

                _handlers[standard_name] = handler_class
                _provider_metadata_map[standard_name] = meta # Store the validated/processed metadata entry

                # Register aliases, checking for conflicts
                for alias in aliases:
                    normalized_alias = alias.lower().replace(" ", "").replace("-", "_")
                    if normalized_alias in _provider_aliases and _provider_aliases[normalized_alias] != standard_name:
                        # Log conflict but allow overwrite - last entry in JSON wins for a given alias
                        日志记录器.warning(f"别名冲突: 提供商 '{standard_name}' 的别名 '{alias}' (标准化: '{normalized_alias}') 覆盖了之前为提供商 '{_provider_aliases[normalized_alias]}' 注册的别名。")
                    _provider_aliases[normalized_alias] = standard_name

                日志记录器.info(f"成功注册提供商 '{standard_name}' 的处理器 (类: {class_name}, 别名: {aliases})")
                registration_count += 1

            except KeyError as key_err:
                # Should be caught by the .get() or initial validation, but kept as safety net
                日志记录器.error(f"关键错误: 处理元数据条目 {meta} 时缺少必需的键 {key_err}。跳过。")
            except Exception as e:
                # Catch unexpected errors during processing of a single entry
                日志记录器.error(f"处理提供商 '{meta.get('standard_name', '未知')}' 的元数据条目时发生意外错误: {e}", exc_info=True)
                # Continue to next entry

        # 5. Final logging and setting initialized flag
        if registration_count == 0:
            日志记录器.warning("初始化完成，但未成功注册任何处理器。请检查元数据文件和日志。")
        else:
            日志记录器.info(f"API 处理器初始化完成。成功注册了 {registration_count} 个处理器。")
            日志记录器.debug(f"最终注册的处理器: {list(_handlers.keys())}")
            日志记录器.debug(f"最终注册的别名: {_provider_aliases}")

        _initialized = True # Mark initialization as complete

    except FileNotFoundError:
        # Logged earlier, ensures _initialized remains False
        日志记录器.critical("处理器初始化失败: 未找到元数据文件。")
        _initialized = False
    except ValueError as ve:
        # Logged earlier (JSON errors, format errors)
        _initialized = False
        日志记录器.critical(f"处理器初始化失败: {ve}")
    except Exception as e:
        # Catch unexpected errors during the overall initialization process
        日志记录器.critical(f"API 处理器初始化期间发生严重意外错误: {str(e)}", exc_info=True)
        _initialized = False
        # Depending on severity, consider re-raising to halt application start
        # raise


# --- Public Factory Functions ---

# Ensure initialize_handlers() is called explicitly at application startup,
# for example, in your main FastAPI application setup.

def get_handler(provider_name_or_alias: str) -> Optional[BaseAPIHandler]:
    """
    根据提供商名称或别名获取已初始化的处理器实例。

    加载配置的优先级:
    1. 环境变量 (根据 metadata 中的 env_prefix)
    2. Provider JSON 配置文件 (根据 metadata 中的 config_path)
    3. 传递给构造函数的基础 config (目前为空)

    Args:
        provider_name_or_alias: 提供商的标准名称或其别名。

    Returns:
        如果找到并成功初始化，则返回处理器实例，否则返回 None。
    """
    global _project_root
    _initialize_factory() # Ensure factory is initialized

    if not _project_root:
        日志记录器.error("无法确定项目根目录，无法加载配置。")
        return None

    normalized_name = provider_name_or_alias.lower().replace("-", "_")
    standard_name = _provider_aliases.get(normalized_name, normalized_name)

    if standard_name not in _handlers:
        日志记录器.error(f"未找到提供商 '{provider_name_or_alias}' (标准化为 '{standard_name}') 的处理器。")
        return None

    handler_class = _handlers[standard_name]

    # 查找对应的元数据
    provider_meta = next((meta for meta in _provider_metadata_map.values() if meta.get("standard_name") == standard_name), None)

    if not provider_meta:
        日志记录器.error(f"严重错误: 找到了处理器类但未找到 '{standard_name}' 的元数据。")
        return None # Should not happen if initialization is correct

    # --- 恢复：移除优化，改回在循环内加载 .env --- 
    # dotenv_path = find_dotenv(raise_error_if_not_found=False)
    # all_env_vars = {**dotenv_values(dotenv_path), **os.environ} 
    # 日志记录器.debug(f"get_handler: 已加载 .env 文件 ({dotenv_path}) 和系统环境变量。")
    # -----------------------------------------

    # --- 简化配置加载逻辑：只从环境变量加载 --- 
    config = {}
    env_prefix = provider_meta.get("env_prefix")
    
    if env_prefix:
        日志记录器.debug(f"正在为提供商 '{standard_name}' 加载前缀为 '{env_prefix}' 的环境变量...")
        # --- 恢复：在需要时加载 --- 
        dotenv_path = find_dotenv(raise_error_if_not_found=False) 
        all_env_vars = {**dotenv_values(dotenv_path), **os.environ} 
        # ------------------------

        prefix_len = len(env_prefix)
        for key, value in all_env_vars.items(): # 使用新加载的 all_env_vars
            if key.startswith(env_prefix):
                config_key = key 
                processed_value = value 
                if value is not None:
                    if value.lower() in ['true', 'false']:
                        processed_value = value.lower() == 'true'
                    else:
                        try:
                            # 尝试转换为 int 或 float
                            if '.' in value:
                                processed_value = float(value)
                            else:
                                processed_value = int(value)
                        except ValueError:
                            pass # 保持为字符串
                
                config[config_key] = processed_value
                # 日志记录器.debug(f"  加载的环境变量: {config_key} = {processed_value}")
        日志记录器.debug(f"为 '{standard_name}' 加载的最终配置键 (来自环境变量): {list(config.keys())}")
    else:
        日志记录器.warning(f"提供商 '{standard_name}' 在元数据中没有定义 'env_prefix'，将不会从环境变量加载配置。")

    # --- 直接将扁平的配置字典传递给 Handler ---
    try:
        # 添加 provider_name 到配置中，方便 Handler 内部使用
        config['provider_name'] = standard_name 
        handler_instance = handler_class(config)
        日志记录器.info(f"成功创建提供商 '{standard_name}' 的处理器实例。")
        return handler_instance
    except Exception as e:
        日志记录器.exception(f"初始化提供商 '{standard_name}' 的处理器时出错: {e}")
        return None

def get_handler_classes() -> Dict[str, Type[BaseAPIHandler]]:
    """
    返回一个字典，将标准提供商名称映射到其处理器类。
    
    返回:
        包含已注册处理器类的字典副本。
    """
    if not _initialized: initialize_handlers()
    return _handlers.copy() # 返回副本以防止外部修改

def get_handler_for_provider(provider: str) -> Type[BaseAPIHandler]:
    """
    获取特定提供商名称或别名的处理器*类*。

    参数:
        provider: API 提供商的名称或别名。

    返回:
        已注册的处理器类型。

    异常:
        ValueError: 如果没有为该提供商注册处理器类。
    """
    if not _initialized: initialize_handlers()
    standard_provider = APIHandlerFactory.standardize_provider_name(provider) # 解析别名
    if standard_provider not in _handlers:
        # 如果未知，错误已在 standardize_provider_name 中记录
        raise ValueError(f"提供商 {standard_provider} (输入: '{provider}') 没有注册处理器类")
    return _handlers[standard_provider]

# --- 添加用于访问元数据的辅助函数 ---

def get_all_provider_metadata() -> List[ProviderMetadata]:
    """
    返回包含所有成功注册的提供商的元数据字典的列表。

    返回:
        已加载和处理的提供商元数据的列表副本。
    """
    if not _initialized: initialize_handlers()
    # 从映射中返回值（元数据字典）的列表
    return list(_provider_metadata_map.values())

def get_provider_metadata(provider_name_or_alias: str) -> Optional[ProviderMetadata]:
    """
    获取特定提供商的元数据字典。

    参数:
        provider: 提供商名称或别名

    返回:
        提供商的元数据字典，如果提供商未知则返回 None
    """
    if not _initialized: initialize_handlers()
    try:
        # 标准化名称以处理别名
        standard_name = APIHandlerFactory.standardize_provider_name(provider_name_or_alias)
        # 返回元数据字典的副本
        meta = _provider_metadata_map.get(standard_name)
        return meta.copy() if meta else None
    except ValueError: # standardize_provider_name 如果提供商未知会抛出
        日志记录器.debug(f"请求了未知提供商 '{provider_name_or_alias}' 的元数据。返回 None。")
        return None

def standardize_provider_name(provider: str) -> str:
    """
    模块级别的辅助函数，用于标准化提供商名称。
    直接调用 APIHandlerFactory.standardize_provider_name 类方法。
    
    参数:
        provider: 提供商名称或别名
        
    返回:
        标准化后的提供商名称
        
    异常:
        ValueError: 如果提供商名称为空或无法解析为已知的标准名称或别名
    """
    return APIHandlerFactory.standardize_provider_name(provider)

def _initialize_factory():
    """
    Internal function to load metadata and register handlers.
    Separated for clarity and potential re-initialization.
    """
    global _handlers, _provider_aliases, _provider_metadata_map, _project_root
    if _provider_metadata_map: # Avoid re-initialization if already done
        # logger.debug("Factory already initialized.")
        return

    _project_root = Path(_PROJECT_ROOT)
    # --- Replace the call to the non-existent function with actual loading logic ---
    loaded_metadata_map = {} # Initialize as empty dict
    try:
        meta_file_path = Path(METADATA_FILE) # Use the constant defined earlier
        if meta_file_path.exists():
             日志记录器.info(f"正在从元数据文件加载: {meta_file_path}")
             with open(meta_file_path, 'r', encoding='utf-8') as f:
                 try:
                     providers_metadata_list: List[ProviderMetadata] = json.load(f)
                     if not isinstance(providers_metadata_list, list):
                         日志记录器.error(f"元数据文件 {meta_file_path} 格式无效: 顶层应为列表。")
                         providers_metadata_list = [] # Reset to empty on format error

                     # Convert list to dict mapping standard_name to metadata dict
                     for meta_entry in providers_metadata_list:
                         if isinstance(meta_entry, dict) and meta_entry.get('standard_name'):
                             loaded_metadata_map[meta_entry['standard_name']] = meta_entry
                         else:
                             日志记录器.warning(f"跳过无效的元数据条目: {meta_entry}")
                     日志记录器.debug(f"成功解析并转换了 {len(loaded_metadata_map)} 条元数据。")

                 except json.JSONDecodeError as json_err:
                     日志记录器.error(f"解析元数据文件 {meta_file_path} 中的 JSON 时出错: {json_err}")
                     # Keep loaded_metadata_map as empty
        else:
             日志记录器.error(f"元数据文件未找到: {meta_file_path}。无法加载处理器元数据。")

    except Exception as load_err:
        日志记录器.critical(f"加载或处理元数据文件 {METADATA_FILE} 时发生严重错误: {load_err}", exc_info=True)
        # Keep loaded_metadata_map as empty on critical error

    # --- End of replacement ---

    if not loaded_metadata_map: # Check if loading resulted in an empty map
        日志记录器.error("Failed to load provider metadata or metadata file is empty/invalid. Factory initialization incomplete.")
        return

    _handlers = {}
    _provider_aliases = {}
    _provider_metadata_map = loaded_metadata_map # Assign the loaded map

    # No need for this line anymore as logging is done during loading
    # 日志记录器.info(f"正在从元数据文件初始化 API 处理器: {METADATA_FILE}")

    # Iterate through the values (metadata dicts) of the loaded map
    for provider_info in _provider_metadata_map.values():
        standard_name = provider_info.get("standard_name")
        module_path = provider_info.get("handler_module_path")
        class_name = provider_info.get("handler_class_name")
        aliases = provider_info.get("aliases", [])

        if not all([standard_name, module_path, class_name]):
            日志记录器.warning(f"跳过元数据条目，信息不完整: {provider_info}")
            continue

        try:
            module = importlib.import_module(module_path)
            handler_class = getattr(module, class_name)

            if not issubclass(handler_class, BaseAPIHandler):
                日志记录器.warning(f"跳过 {class_name}: 它不是 BaseAPIHandler 的子类。")
                continue

            # 注册标准名称
            _handlers[standard_name] = handler_class
            日志记录器.info(f"成功注册提供商 '{standard_name}' 的处理器 (类: {class_name}, 别名: {aliases})")

            # 注册别名
            for alias in aliases:
                normalized_alias = alias.lower().replace("-", "_")
                if normalized_alias in _provider_aliases and _provider_aliases[normalized_alias] != standard_name:
                    日志记录器.warning(f"别名冲突: '{alias}' (标准化为 '{normalized_alias}') 已映射到 '{_provider_aliases[normalized_alias]}', 无法重新映射到 '{standard_name}'。")
                elif normalized_alias != standard_name: # Don't map standard name to itself as an alias
                    _provider_aliases[normalized_alias] = standard_name
                    日志记录器.debug(f"  映射别名 '{alias}' -> '{standard_name}'")

        except ImportError as e:
            日志记录器.error(f"导入提供商模块失败 '{module_path}': {e}")
        except AttributeError as e:
            日志记录器.error(f"在模块 '{module_path}' 中找不到处理器类 '{class_name}': {e}")
        except Exception as e:
            日志记录器.error(f"注册提供商 '{standard_name}' 时发生未知错误: {e}", exc_info=True)

    日志记录器.info(f"API 处理器初始化完成。成功注册了 {len(_handlers)} 个处理器。")
    日志记录器.debug(f"最终注册的处理器: {list(_handlers.keys())}")
    日志记录器.debug(f"最终注册的别名: {_provider_aliases}")