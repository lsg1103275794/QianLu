"""
提供商配置加载器模块，用于加载和解析提供商配置文件
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, TypedDict, Union, Literal
import dotenv

# 配置日志
logger = logging.getLogger(__name__)

# 确定项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
PROVIDERS_CONFIG_DIR = CONFIG_DIR / "providers"

# 如果提供商配置目录不存在，创建它
PROVIDERS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

class ParameterConfig(TypedDict, total=False):
    """参数配置结构"""
    name: str
    env_var: str
    type: str
    default: Union[str, int, float, bool, None]
    required: bool
    description: str
    min_value: Optional[Union[int, float]]
    max_value: Optional[Union[int, float]]

class ProviderConfig(TypedDict):
    """提供商配置结构"""
    standard_name: str
    display_name: str
    handler_module_path: str
    handler_class_name: str
    aliases: List[str]
    env_prefix: str
    api_parameters: Dict[str, List[ParameterConfig]]
    credentials: List[ParameterConfig]
    endpoint_config: ParameterConfig
    model_config: ParameterConfig
    other_settings: List[ParameterConfig]

class ConfigLoaderError(Exception):
    """配置加载器错误"""
    pass

class ProviderConfigLoader:
    """提供商配置加载器类"""
    
    def __init__(self):
        """初始化提供商配置加载器"""
        self.providers_meta_path = CONFIG_DIR / "providers_meta.json"
        self.provider_configs: Dict[str, ProviderConfig] = {}
        self._load_provider_configs()
    
    def _load_provider_configs(self) -> None:
        """加载所有提供商配置"""
        try:
            # 先加载提供商元数据，获取标准名称列表
            providers_meta = self._load_providers_meta()
            if not providers_meta:
                logger.warning("无法加载providers_meta.json文件，无法继续加载提供商配置")
                return
            
            # 对每个提供商，尝试加载其配置文件
            for provider_meta in providers_meta:
                standard_name = provider_meta.get("standard_name")
                if not standard_name:
                    logger.warning(f"提供商元数据缺少standard_name字段: {provider_meta}")
                    continue
                
                # 尝试加载提供商配置文件
                config_path = PROVIDERS_CONFIG_DIR / f"{standard_name}.json"
                if config_path.exists():
                    try:
                        with open(config_path, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                        
                        # 验证配置文件结构
                        if self._validate_provider_config(config):
                            self.provider_configs[standard_name] = config
                            logger.info(f"已加载提供商配置: {standard_name}")
                        else:
                            logger.warning(f"提供商配置文件格式无效: {standard_name}")
                    except Exception as e:
                        logger.error(f"加载提供商配置文件时出错 {standard_name}: {e}")
                else:
                    # 如果配置文件不存在，则使用元数据和模板生成默认配置
                    default_config = self._generate_default_config(provider_meta)
                    if default_config:
                        self.provider_configs[standard_name] = default_config
                        logger.info(f"已生成提供商默认配置: {standard_name}")
                    else:
                        logger.warning(f"无法为提供商生成默认配置: {standard_name}")
            
            logger.info(f"已加载 {len(self.provider_configs)} 个提供商配置")
        
        except Exception as e:
            logger.error(f"加载提供商配置过程中出错: {e}")
    
    def _load_providers_meta(self) -> List[Dict[str, Any]]:
        """加载提供商元数据文件"""
        try:
            if not self.providers_meta_path.exists():
                logger.error(f"提供商元数据文件不存在: {self.providers_meta_path}")
                return []
            
            with open(self.providers_meta_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if not isinstance(data, list):
                logger.error(f"提供商元数据文件格式无效，应为列表: {self.providers_meta_path}")
                return []
                
            return data
        
        except Exception as e:
            logger.error(f"加载提供商元数据文件时出错: {e}")
            return []
    
    def _validate_provider_config(self, config: Dict[str, Any]) -> bool:
        """验证提供商配置是否符合要求的结构"""
        # 基本必须的字段
        required_fields = [
            "standard_name", "display_name", "handler_module_path", 
            "handler_class_name", "aliases", "env_prefix"
        ]
        
        for field in required_fields:
            if field not in config:
                logger.warning(f"提供商配置缺少必要字段: {field}")
                return False
        
        # TODO: 进行更详细的结构验证
        return True
    
    def _generate_default_config(self, provider_meta: Dict[str, Any]) -> Optional[ProviderConfig]:
        """根据提供商元数据生成默认配置"""
        try:
            # 加载配置模板
            template_path = CONFIG_DIR / "provider_config_template.json"
            if not template_path.exists():
                logger.error(f"提供商配置模板文件不存在: {template_path}")
                return None
            
            with open(template_path, 'r', encoding='utf-8') as f:
                template = json.load(f)
            
            # 使用元数据填充模板
            config = template.copy()
            
            # 更新基本信息
            for key in ["standard_name", "display_name", "handler_module_path", 
                         "handler_class_name", "aliases", "env_prefix"]:
                if key in provider_meta:
                    config[key] = provider_meta[key]
            
            # 替换所有${ENV_PREFIX}占位符
            env_prefix = provider_meta.get("env_prefix", "")
            config_str = json.dumps(config)
            config_str = config_str.replace("${ENV_PREFIX}", env_prefix)
            config = json.loads(config_str)
            
            # 保存生成的默认配置
            self._save_provider_config(config)
            
            return config
            
        except Exception as e:
            logger.error(f"生成提供商默认配置时出错: {e}")
            return None
    
    def _save_provider_config(self, config: ProviderConfig) -> bool:
        """保存提供商配置到文件"""
        try:
            standard_name = config.get("standard_name")
            if not standard_name:
                logger.error("无法保存提供商配置，缺少standard_name字段")
                return False
            
            config_path = PROVIDERS_CONFIG_DIR / f"{standard_name}.json"
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"已保存提供商配置到文件: {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存提供商配置文件时出错: {e}")
            return False
    
    def get_all_providers(self) -> List[str]:
        """获取所有已加载的提供商标准名称列表"""
        return list(self.provider_configs.keys())
    
    def get_provider_config(self, provider_name: str) -> Optional[ProviderConfig]:
        """获取指定提供商的配置"""
        # TODO: 这里需要实现标准化名称的处理
        return self.provider_configs.get(provider_name)
    
    def get_parameter_env_value(self, provider_name: str, param_name: str, 
                                param_type: Literal["runtime", "default", "credential", "endpoint", "model", "other"] = "runtime") -> Any:
        """获取提供商参数的当前环境变量值"""
        config = self.get_provider_config(provider_name)
        if not config:
            logger.warning(f"找不到提供商配置: {provider_name}")
            return None
        
        # 根据参数类型查找对应的参数列表
        param_list = []
        if param_type == "runtime":
            param_list = config.get("api_parameters", {}).get("runtime", [])
        elif param_type == "default":
            param_list = config.get("api_parameters", {}).get("default", [])
        elif param_type == "credential":
            param_list = config.get("credentials", [])
        elif param_type == "endpoint":
            endpoint_config = config.get("endpoint_config")
            if endpoint_config and endpoint_config.get("name") == param_name:
                param_list = [endpoint_config]
        elif param_type == "model":
            model_config = config.get("model_config")
            if model_config and model_config.get("name") == param_name:
                param_list = [model_config]
        elif param_type == "other":
            param_list = config.get("other_settings", [])
        
        # 查找匹配的参数
        for param in param_list:
            if param.get("name") == param_name:
                env_var = param.get("env_var")
                if not env_var:
                    logger.warning(f"参数 {param_name} 缺少env_var字段")
                    return None
                
                # 从.env文件读取值
                dotenv_path = dotenv.find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=True)
                if not dotenv_path:
                    logger.warning("无法找到.env文件")
                    return None
                
                env_values = dotenv.dotenv_values(dotenv_path)
                value = env_values.get(env_var)
                
                # 根据参数类型转换值
                if value is not None:
                    param_type_str = param.get("type", "text")
                    try:
                        if param_type_str == "int":
                            return int(value)
                        elif param_type_str == "float":
                            return float(value)
                        elif param_type_str == "boolean":
                            return value.lower() in ("true", "1", "yes", "y")
                        else:
                            return value
                    except (ValueError, TypeError):
                        logger.warning(f"无法将环境变量值 '{value}' 转换为 {param_type_str} 类型")
                        return None
                
                # 如果环境变量不存在，返回默认值
                return param.get("default")
        
        logger.warning(f"在提供商 {provider_name} 的配置中找不到参数 {param_name}")
        return None
    
    def get_handler_config(self, provider_name: str) -> Dict[str, Any]:
        """获取用于实例化处理器的配置字典"""
        config = self.get_provider_config(provider_name)
        if not config:
            logger.warning(f"找不到提供商配置: {provider_name}")
            return {}
        
        # 从.env文件读取最新值
        dotenv_path = dotenv.find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=True)
        if not dotenv_path:
            logger.warning("无法找到.env文件，将使用默认值")
            env_values = {}
        else:
            env_values = dotenv.dotenv_values(dotenv_path)
        
        # 构建处理器配置
        handler_config = {
            "provider_name": provider_name,
            "credentials": {}
        }
        
        # 处理凭据
        for cred in config.get("credentials", []):
            name = cred.get("name")
            env_var = cred.get("env_var")
            if name and env_var and env_var in env_values:
                handler_config["credentials"][name] = env_values[env_var]
        
        # 处理端点配置
        endpoint_config = config.get("endpoint_config", {})
        if endpoint_config:
            env_var = endpoint_config.get("env_var")
            if env_var and env_var in env_values:
                handler_config["endpoint"] = env_values[env_var]
            elif "default" in endpoint_config:
                handler_config["endpoint"] = endpoint_config["default"]
        
        # 处理模型配置
        model_config = config.get("model_config", {})
        if model_config:
            env_var = model_config.get("env_var")
            if env_var and env_var in env_values:
                handler_config["default_model"] = env_values[env_var]
            elif "default" in model_config:
                handler_config["default_model"] = model_config["default"]
        
        # 处理运行时参数
        runtime_params = config.get("api_parameters", {}).get("runtime", [])
        for param in runtime_params:
            name = param.get("name")
            env_var = param.get("env_var")
            if name and env_var:
                if env_var in env_values:
                    value = env_values[env_var]
                    # 根据类型转换值
                    param_type = param.get("type", "text")
                    try:
                        if param_type == "int":
                            handler_config[name] = int(value)
                        elif param_type == "float":
                            handler_config[name] = float(value)
                        elif param_type == "boolean":
                            handler_config[name] = value.lower() in ("true", "1", "yes", "y")
                        else:
                            handler_config[name] = value
                    except (ValueError, TypeError):
                        logger.warning(f"无法将 {env_var} 的值 '{value}' 转换为 {param_type} 类型")
                        if "default" in param:
                            handler_config[name] = param["default"]
                elif "default" in param:
                    handler_config[name] = param["default"]
        
        # 处理其他设置
        other_settings = config.get("other_settings", [])
        for setting in other_settings:
            name = setting.get("name")
            env_var = setting.get("env_var")
            if name and env_var:
                if env_var in env_values:
                    value = env_values[env_var]
                    # 根据类型转换值
                    setting_type = setting.get("type", "text")
                    try:
                        if setting_type == "int":
                            handler_config[name] = int(value)
                        elif setting_type == "float":
                            handler_config[name] = float(value)
                        elif setting_type == "boolean":
                            handler_config[name] = value.lower() in ("true", "1", "yes", "y")
                        else:
                            handler_config[name] = value
                    except (ValueError, TypeError):
                        logger.warning(f"无法将 {env_var} 的值 '{value}' 转换为 {setting_type} 类型")
                        if "default" in setting:
                            handler_config[name] = setting["default"]
                elif "default" in setting:
                    handler_config[name] = setting["default"]
        
        return handler_config


# 创建全局单例实例
provider_config_loader = ProviderConfigLoader() 