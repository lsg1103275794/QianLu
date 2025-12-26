"""
Base API handler class.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Union
import dotenv
import logging
from src.utils.logging import logger
# 延迟导入，避免循环依赖
# from src.config.api_manager import api_manager

class BaseAPIHandler(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider_name = config.get("provider_name", "unknown")
        self._validate_config()

    def _validate_config(self):
        """Validate the configuration."""
        # --- 修改：不再强制要求配置，只记录警告 --- 
        # required_fields = self.get_required_config_fields()
        # for field in required_fields:
        #     if field not in self.config:
        #         # Raise ValueError(f"Missing required configuration field: {field}")
        #         logger.warning(f"Provider '{self.provider_name}': Missing configuration field: {field}")
        # --- 校验逻辑移到需要的地方，例如 test_connection 或 generate ---
        pass # Validation moved to methods that require specific fields
    
    def get_current_param(self, param_name: str, param_type: Optional[str] = None, default_value: Any = None) -> Any:
        """
        从.env文件实时读取指定参数的值。
        优先查找运行时参数（如PROVIDER_PARAM），如果不存在则查找默认参数（如PROVIDER_DEFAULT_PARAM）。
        
        参数:
            param_name: 参数名称，如'temperature'、'max_tokens'等
            param_type: 参数类型，用于转换值，如'int'、'float'、'bool'，默认为None（不转换）
            default_value: 如果参数不存在，返回的默认值
            
        返回:
            参数的值，如果参数不存在或转换失败，则返回default_value
        """
        try:
            # 延迟导入，避免循环依赖
            from src.providers.factory import get_provider_metadata
            
            # 获取提供商元数据以获取环境变量前缀
            provider_meta = get_provider_metadata(self.provider_name)
            if not provider_meta:
                logger.warning(f"无法获取提供商 '{self.provider_name}' 的元数据，使用默认值")
                return default_value
            
            env_prefix = provider_meta.get('env_prefix', '')
            if not env_prefix:
                logger.warning(f"提供商 '{self.provider_name}' 元数据中没有env_prefix，使用默认值")
                return default_value
            
            # 从.env文件读取最新值
            dotenv_path = dotenv.find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=True)
            if not dotenv_path:
                logger.warning(f"无法找到.env文件，使用默认值")
                return default_value
            
            env_values = dotenv.dotenv_values(dotenv_path)
            
            # 尝试先读取运行时参数
            runtime_param_name = f"{env_prefix}{param_name.upper()}"
            value = env_values.get(runtime_param_name)
            
            # 如果运行时参数不存在，尝试读取默认参数
            if value is None:
                default_param_name = f"{env_prefix}DEFAULT_{param_name.upper()}"
                value = env_values.get(default_param_name)
            
            # 如果两者都不存在，返回默认值
            if value is None:
                return default_value
            
            # 根据指定的类型转换值
            if param_type == 'int':
                try:
                    return int(value)
                except (ValueError, TypeError):
                    logger.warning(f"无法将 {runtime_param_name} 的值 '{value}' 转换为整数，使用默认值")
                    return default_value
            elif param_type == 'float':
                try:
                    return float(value)
                except (ValueError, TypeError):
                    logger.warning(f"无法将 {runtime_param_name} 的值 '{value}' 转换为浮点数，使用默认值")
                    return default_value
            elif param_type == 'bool':
                return value.lower() in ('true', '1', 'yes', 'y', 'on')
            else:
                return value
                
        except Exception as e:
            logger.error(f"获取参数 {param_name} 时出错: {e}")
            return default_value

    @abstractmethod
    def get_required_config_fields(self) -> List[str]:
        """Get the list of required configuration fields."""
        pass

    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """Get the list of available models."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate text using the API."""
        pass

    async def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Generate text using the API. Default implementation calls self.generate."""
        logger.debug(f"BaseAPIHandler.generate_text called for {self.provider_name}. Defaulting to self.generate.")
        return await self.generate(prompt, model, **kwargs)

    async def generate_report(self, topic: str, model: Optional[str] = None, **kwargs) -> str:
        """Generate a report using the standard text generation logic with a specific report prompt."""
        logger.info(f"[{self.provider_name}] BaseAPIHandler.generate_report called for topic: '{topic}' with model: '{model or getattr(self, 'default_model', 'Not Specified')}'")
        
        report_prompt = (
            f"你是一位直接输出结果的专业行业分析师。你的唯一任务是严格按照用户提供的资料（如果有）和针对主题\"{topic}\"的以下结构，生成一份Markdown格式的研报。不要添加任何解释、开场白、思考过程或总结性发言。直接开始输出研报正文。\n\n" 
            "研报结构：\n"
            "1.  核心摘要：对整个主题和关键发现进行高度概括。\n"
            "2.  主要观点：列出3-5个基于所提供资料的最重要观点或发现。\n"
            "3.  数据支撑（可选）：如果资料中包含具体数据，请提及。\n"
            "4.  潜在影响或未来趋势：基于资料进行简要推测。\n"
            "5.  关键信息来源（如果基于外部搜索）：列出报告中引用的主要信息来源的标题和URL。\n"
            "6.  总结性观点与关键词 (keywords)。\n\n" 
            f"研报主题：\"{topic}\"\n\n"
            "再次强调：严格按照以上结构直接输出Markdown研报，不要有任何额外内容。"
        )
        
        # Call the existing text generation method, which in turn calls the abstract 'generate' method
        return await self.generate_text(prompt=report_prompt, model=model, **kwargs)

    async def check_status(self) -> Dict[str, Any]:
        """检查API提供商的状态，默认实现通过检查配置和测试模型列表获取"""
        logger.info(f"正在检查提供商 '{self.provider_name}' 的状态")
        
        # 从API管理器获取配置状态
        try:
            # 延迟导入，避免循环依赖
            from src.config.api_manager import api_manager
            is_configured, status_msg = api_manager.is_provider_configured(self.provider_name)
            logger.debug(f"提供商 '{self.provider_name}' 配置状态: is_configured={is_configured}, msg='{status_msg}'")
        except Exception as e:
            logger.error(f"检查提供商 '{self.provider_name}' 配置时出错: {e}")
            is_configured = False
            status_msg = f"检查配置时出错: {str(e)}"
        
        status = {
            "is_configured": is_configured,
            "status_message": status_msg
        }
        
        # 如果配置正确，尝试获取模型列表以验证连接
        if is_configured:
            try:
                logger.debug(f"正在检查提供商 '{self.provider_name}' 的模型列表")
                models = await self.get_available_models()
                
                if models and len(models) > 0:
                    logger.info(f"提供商 '{self.provider_name}' 可用模型: {len(models)} 个")
                    status["models_available"] = len(models)
                    status["models_list"] = models[:5]  # 只返回前5个模型名称，避免响应过大
                    status["connection_test"] = "success"
                else:
                    logger.warning(f"提供商 '{self.provider_name}' 模型列表为空")
                    status["models_available"] = 0
                    status["connection_test"] = "warning"
                    status["connection_warning"] = "获取模型列表成功，但模型列表为空"
            except Exception as e:
                logger.warning(f"提供商 '{self.provider_name}' 连接测试失败: {e}")
                status["connection_test"] = "error"
                status["connection_error"] = str(e)
        
        logger.info(f"提供商 '{self.provider_name}' 状态检查完成: {status}")
        return status

    async def _handle_error(self, error: Exception) -> None:
        """Handle API errors."""
        logger.error(f"API error: {str(error)}")
        raise error 

    async def test_connection(self, model: Optional[str] = None) -> Dict[str, str]:
        """
        Default implementation for testing API connection.
        Attempts to use 'chat' or 'generate' method with a minimal prompt.
        Returns a dictionary with 'status' and 'message'.
        Handlers can override this if a specific test (e.g., status endpoint) is available.
        """
        import asyncio
        from src.validation.error_handler import APIConnectionError, APIResponseError, APIError, APITimeoutError, ConfigurationError
        
        target_model = model or getattr(self, 'default_model', None)
        if not target_model:
            logger.error(f"Cannot test connection for {self.provider_name}: Model not specified and no default model available.")
            # Raise ConfigurationError or return error dict based on desired handling
            # raise ConfigurationError(f"No model specified and no default model configured for {self.provider_name}.")
            return {"status": "error", "message": "测试失败：未指定模型且未配置默认模型"}
            
        logger.info(f"Testing connection for {self.provider_name} using model '{target_model}' (default test_connection)")
        
        test_prompt = "Test connection, respond OK."
        test_messages = [{"role": "user", "content": test_prompt}]
        max_test_tokens = 5
        test_temp = 0.1
        timeout_seconds = 30.0 # Timeout for the test connection call (Increased from 15.0)
        
        handler_method = None
        payload = {}
        method_name = "unknown"
        
        # Prefer chat method if available and async
        if hasattr(self, 'chat') and asyncio.iscoroutinefunction(getattr(self, 'chat')):
            handler_method = self.chat
            payload = {"messages": test_messages, "model": target_model, "stream": False, "max_tokens": max_test_tokens, "temperature": test_temp}
            method_name = "chat"
        # Fallback to generate_text (or generate) if available and async
        elif hasattr(self, 'generate_text') and asyncio.iscoroutinefunction(getattr(self, 'generate_text')):
            handler_method = self.generate_text
            payload = {"prompt": test_prompt, "model": target_model, "max_tokens": max_test_tokens, "temperature": test_temp}
            method_name = "generate_text"
        elif hasattr(self, 'generate') and asyncio.iscoroutinefunction(getattr(self, 'generate')):
            handler_method = self.generate # Some handlers might only have generate
            payload = {"prompt": test_prompt, "model": target_model, "max_tokens": max_test_tokens, "temperature": test_temp}
            method_name = "generate"
        else:
            logger.error(f"Handler {self.provider_name} has no suitable async chat, generate_text, or generate method for default test_connection.")
            return {"status": "error", "message": "测试失败：Handler 未实现可用的测试方法"}

        try:
            logger.debug(f"Calling {method_name} for connection test with timeout {timeout_seconds}s")
            # We don't care about the response content, just if it succeeds
            await asyncio.wait_for(handler_method(**payload), timeout=timeout_seconds)
            
            # If the call completes without raising an exception, it's a success
            success_message = f"成功通过 {method_name} 方法连接到 {self.provider_name} 模型 '{target_model}'"
            logger.info(success_message)
            return {"status": "success", "message": success_message}
            
        except asyncio.TimeoutError:
            error_message = f"连接测试超时 ({timeout_seconds}秒)"
            logger.error(f"{self.provider_name} connection test failed: {error_message}")
            return {"status": "error", "message": error_message}
        except APIConnectionError as e:
            error_message = f"连接测试失败 (网络/连接错误): {str(e)}"
            logger.error(f"{self.provider_name} connection test failed: {error_message}", exc_info=True)
            return {"status": "error", "message": error_message}
        except APIResponseError as e:
            error_message = f"连接测试失败 (API响应错误 {e.status_code}): {str(e)}"
            logger.error(f"{self.provider_name} connection test failed: {error_message}", exc_info=True)
            return {"status": "error", "message": error_message}
        except APIError as e: # Catch generic API errors from handlers
            error_message = f"连接测试失败 (API错误): {str(e)}"
            logger.error(f"{self.provider_name} connection test failed: {error_message}", exc_info=True)
            return {"status": "error", "message": error_message}
        except Exception as e:
            error_message = f"连接测试时发生意外错误: {type(e).__name__} - {str(e)}"
            logger.error(f"{self.provider_name} connection test failed: {error_message}", exc_info=True)
            return {"status": "error", "message": error_message} 