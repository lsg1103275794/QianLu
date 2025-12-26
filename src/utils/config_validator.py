import json
import jsonschema
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple

logger = logging.getLogger(__name__)

class ConfigValidator:
    """
    配置验证器，用于验证API配置、环境变量等。
    提供验证和错误报告功能。
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置验证器。
        
        参数:
            config_dir: 配置目录路径，如果为None，则使用默认路径
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # 默认配置目录在项目根目录的config文件夹
            self.config_dir = Path(__file__).resolve().parent.parent.parent / "config"
        
        # 存储错误消息
        self.errors: List[str] = []
        # 存储警告消息
        self.warnings: List[str] = []
        
        logger.info(f"ConfigValidator 初始化，配置目录: {self.config_dir}")
    
    def validate_api_configs(self) -> bool:
        """
        验证API配置文件是否有效。
        
        返回:
            bool: 如果验证通过，则返回True；否则返回False
        """
        self.errors = []
        self.warnings = []
        
        # 检查配置文件是否存在
        api_config_path = self.config_dir / "api_configs.json"
        api_schema_path = self.config_dir / "api_configs_schema.json"
        
        if not api_config_path.exists():
            self.errors.append(f"API配置文件不存在: {api_config_path}")
            return False
        
        if not api_schema_path.exists():
            self.warnings.append(f"API配置模式文件不存在: {api_schema_path}，将跳过模式验证")
        
        # 尝试加载配置文件
        try:
            with open(api_config_path, 'r', encoding='utf-8') as f:
                api_configs = json.load(f)
            logger.debug(f"成功加载API配置文件: {api_config_path}")
        except json.JSONDecodeError as e:
            self.errors.append(f"无法解析API配置文件: {e}")
            return False
        except Exception as e:
            self.errors.append(f"读取API配置文件时出错: {e}")
            return False
        
        # 检查基本结构
        if not isinstance(api_configs, dict):
            self.errors.append("API配置必须是一个字典")
            return False
        
        if "providers" not in api_configs:
            self.errors.append("API配置缺少 'providers' 字段")
            return False
        
        if not isinstance(api_configs["providers"], list):
            self.errors.append("API配置中的 'providers' 字段必须是一个列表")
            return False
        
        # 如果模式文件存在，进行模式验证
        if api_schema_path.exists():
            try:
                with open(api_schema_path, 'r', encoding='utf-8') as f:
                    api_schema = json.load(f)
                logger.debug(f"成功加载API模式文件: {api_schema_path}")
                
                # 使用jsonschema进行验证
                try:
                    jsonschema.validate(instance=api_configs, schema=api_schema)
                    logger.info("API配置通过模式验证")
                except jsonschema.exceptions.ValidationError as e:
                    self.errors.append(f"API配置不符合模式: {e.message}")
                    return False
            except json.JSONDecodeError as e:
                self.warnings.append(f"无法解析API模式文件: {e}，将跳过模式验证")
            except Exception as e:
                self.warnings.append(f"读取API模式文件时出错: {e}，将跳过模式验证")
        
        # 进行额外的配置验证
        for provider in api_configs["providers"]:
            if "name" not in provider:
                self.errors.append(f"API提供商缺少 'name' 字段: {provider}")
                continue
            
            provider_name = provider["name"]
            logger.debug(f"验证API提供商: {provider_name}")
            
            # 检查必要的字段
            if "display_name" not in provider:
                self.warnings.append(f"API提供商 '{provider_name}' 缺少 'display_name' 字段")
            
            if "default_model" not in provider:
                self.warnings.append(f"API提供商 '{provider_name}' 缺少 'default_model' 字段")
            
            # 检查环境变量配置
            if "env_configs" in provider:
                if not isinstance(provider["env_configs"], list):
                    self.errors.append(f"API提供商 '{provider_name}' 的 'env_configs' 必须是一个列表")
                else:
                    # 检查每个环境变量配置
                    for env_config in provider["env_configs"]:
                        if "env_name" not in env_config:
                            self.errors.append(f"API提供商 '{provider_name}' 的环境变量配置缺少 'env_name' 字段")
                        
                        if "required" in env_config and env_config["required"]:
                            env_name = env_config.get("env_name", "未知")
                            if not os.environ.get(env_name):
                                self.warnings.append(f"缺少必要的环境变量: {env_name} (对于 {provider_name})")
        
        # 如果有错误，则验证失败
        if self.errors:
            logger.error(f"API配置验证失败，共有 {len(self.errors)} 个错误")
            return False
        
        # 如果有警告，则记录但仍然通过验证
        if self.warnings:
            logger.warning(f"API配置验证通过，但有 {len(self.warnings)} 个警告")
        else:
            logger.info("API配置验证成功，没有发现问题")
        
        return True
    
    def validate_env_variables(self) -> bool:
        """
        验证环境变量是否有效。
        
        返回:
            bool: 如果验证通过，则返回True；否则返回False
        """
        self.errors = []
        self.warnings = []
        
        # 检查基本必要的环境变量
        essential_vars = [
            "DEFAULT_PROVIDER"  # 默认的API提供商
        ]
        
        for var in essential_vars:
            if not os.environ.get(var):
                self.warnings.append(f"缺少推荐的环境变量: {var}")
        
        # 验证API配置，获取所有提供商的环境变量需求
        api_config_path = self.config_dir / "api_configs.json"
        if not api_config_path.exists():
            self.errors.append(f"无法验证API环境变量，配置文件不存在: {api_config_path}")
            return False
        
        try:
            with open(api_config_path, 'r', encoding='utf-8') as f:
                api_configs = json.load(f)
            
            # 获取默认提供商
            default_provider = os.environ.get("DEFAULT_PROVIDER")
            
            # 检查所有提供商的环境变量
            if "providers" in api_configs and isinstance(api_configs["providers"], list):
                for provider in api_configs["providers"]:
                    provider_name = provider.get("name")
                    
                    # 如果是默认提供商，更严格地检查环境变量
                    is_default = default_provider and provider_name == default_provider
                    
                    if "env_configs" in provider and isinstance(provider["env_configs"], list):
                        for env_config in provider["env_configs"]:
                            env_name = env_config.get("env_name")
                            if not env_name:
                                continue
                            
                            is_required = env_config.get("required", False)
                            
                            if is_required and is_default and not os.environ.get(env_name):
                                self.errors.append(f"默认提供商 '{provider_name}' 缺少必要的环境变量: {env_name}")
                            elif is_required and not os.environ.get(env_name):
                                self.warnings.append(f"提供商 '{provider_name}' 缺少必要的环境变量: {env_name}")
        except Exception as e:
            self.errors.append(f"验证环境变量时出错: {e}")
            return False
        
        # 如果有错误，则验证失败
        if self.errors:
            logger.error(f"环境变量验证失败，共有 {len(self.errors)} 个错误")
            return False
        
        # 如果有警告，则记录但仍然通过验证
        if self.warnings:
            logger.warning(f"环境变量验证通过，但有 {len(self.warnings)} 个警告")
        else:
            logger.info("环境变量验证成功，没有发现问题")
        
        return True
    
    def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """
        验证所有配置。
        
        返回:
            Tuple[bool, List[str], List[str]]: (是否通过验证, 错误列表, 警告列表)
        """
        api_valid = self.validate_api_configs()
        env_valid = self.validate_env_variables()
        
        # 合并错误和警告
        all_errors = list(self.errors)
        all_warnings = list(self.warnings)
        
        all_valid = api_valid and env_valid
        
        if all_valid:
            if all_warnings:
                logger.warning(f"所有配置验证通过，但有 {len(all_warnings)} 个警告")
            else:
                logger.info("所有配置验证成功，没有发现问题")
        else:
            logger.error(f"配置验证失败，共有 {len(all_errors)} 个错误和 {len(all_warnings)} 个警告")
        
        return all_valid, all_errors, all_warnings
    
    def get_validation_report(self) -> Dict[str, Any]:
        """
        获取验证报告。
        
        返回:
            Dict[str, Any]: 包含验证结果的字典
        """
        all_valid, all_errors, all_warnings = self.validate_all()
        
        return {
            "valid": all_valid,
            "errors": all_errors,
            "warnings": all_warnings,
            "error_count": len(all_errors),
            "warning_count": len(all_warnings)
        }


# 如果作为脚本运行，则执行验证并打印结果
if __name__ == "__main__":
    # 设置日志格式
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    validator = ConfigValidator()
    valid, errors, warnings = validator.validate_all()
    
    print(f"\n{'=' * 50}")
    print(f"配置验证结果: {'通过' if valid else '失败'}")
    print(f"{'=' * 50}")
    
    if errors:
        print(f"\n错误 ({len(errors)}):")
        for i, error in enumerate(errors, 1):
            print(f"{i}. {error}")
    
    if warnings:
        print(f"\n警告 ({len(warnings)}):")
        for i, warning in enumerate(warnings, 1):
            print(f"{i}. {warning}")
    
    if not errors and not warnings:
        print("\n未发现任何问题，配置有效。")
    
    print(f"\n{'=' * 50}\n") 