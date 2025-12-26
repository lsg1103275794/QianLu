"""
Ollama Local API handler implementation.
"""
import json
import aiohttp
import os
from typing import Optional, Dict, Any, List, AsyncGenerator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
import logging
import asyncio
from dotenv import dotenv_values

from src.utils.logging import logger
from src.providers.base import BaseAPIHandler
from src.validation.error_handler import ConfigurationError, APIConnectionError, APIResponseError, APIResponseFormatError, APITimeoutError, APIError
from src.utils.retry import is_retryable_exception

class OllamaLocalHandler(BaseAPIHandler):
    """Handles interaction with Ollama Local API."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # 设置提供商名称
        self.provider_name = config.get('provider_name', 'ollama_local')
        # 确保 endpoint 始终有默认值，如果为空则使用默认地址
        endpoint = config.get('endpoint', '')
        self.endpoint = endpoint if endpoint else 'http://localhost:11434'
        self.default_model = config.get('default_model', 'deepseek-r1:8b')
        
        # 更新默认参数，使用更合理的值
        self.default_api_params = {
            'temperature': 0.7,
            'top_p': 1.0,
            'max_tokens': 16000,  # 默认更大的值，环境变量会覆盖这个值
        }
        
        # 尝试从环境变量加载参数
        temp_str = os.environ.get('OLLAMA_TEMPERATURE')
        if temp_str:
            try:
                self.default_api_params['temperature'] = float(temp_str)
            except ValueError:
                logger.warning(f"无效的OLLAMA_TEMPERATURE环境变量值: '{temp_str}'")
        
        max_tokens_str = os.environ.get('OLLAMA_MAX_TOKENS')
        if max_tokens_str:
            try:
                self.default_api_params['max_tokens'] = int(max_tokens_str)
            except ValueError:
                logger.warning(f"无效的OLLAMA_MAX_TOKENS环境变量值: '{max_tokens_str}'")
        
        top_p_str = os.environ.get('OLLAMA_TOP_P')
        if top_p_str:
            try:
                self.default_api_params['top_p'] = float(top_p_str)
            except ValueError:
                logger.warning(f"无效的OLLAMA_TOP_P环境变量值: '{top_p_str}'")
        
        self.request_timeout = config.get('request_timeout', 60)
        
        # Ensure endpoints are set correctly
        if self.endpoint.endswith('/'):
            self.endpoint = self.endpoint.rstrip('/')
            
        logger.info(f"Ollama Local Handler Initialized: Name='{self.provider_name}', Endpoint='{self.endpoint}', DefaultModel='{self.default_model}'")

    def get_required_config_fields(self) -> List[str]:
        """Get the list of required configuration fields."""
        return []

    async def get_available_models(self) -> list:
        """
        获取Ollama可用的模型列表
        返回格式：[{name: 模型名, id: 模型ID}]
        """
        try:
            # 从Ollama获取模型列表
            logger.info(f"正在从Ollama获取可用模型列表，请求URL: {self.endpoint}/api/tags")
            # 使用 GET 方法调用 /api/tags，并且不需要 payload
            response = await self._make_request("/api/tags", method="GET", payload=None) 
            
            if not response or not isinstance(response, dict) or "models" not in response:
                logger.warning(f"Ollama API响应格式异常: {response}")
                return []
            
            # 处理响应数据，构建标准格式的模型列表
            model_list = []
            for model in response.get("models", []):
                model_name = model.get("name")
                if not model_name:
                    continue
                    
                # 将Ollama格式的模型信息转换为标准格式
                model_entry = {
                    "id": model_name,
                    "name": model_name,
                    "provider": self.provider_name
                }
                model_list.append(model_entry)
                
            logger.info(f"成功获取Ollama模型列表，总计{len(model_list)}个模型")
            return model_list
        except Exception as e:
            logger.exception(f"获取Ollama模型列表时出错: {str(e)}")
            # 遇到错误时返回空列表而不是抛出异常，确保UI不会崩溃
            return []

    async def check_service_status(self) -> Dict[str, Any]:
        """
        检查Ollama服务状态
        返回格式: {
            "status": "available" | "unavailable",
            "message": "详细信息",
            "endpoint": "当前使用的终端URL"
        }
        """
        try:
            # 尝试调用API检查服务状态
            logger.info(f"正在检查Ollama服务状态: {self.endpoint}")
            # 调用一个轻量级的接口来验证连接
            await self._make_request("/api/version", {})
            
            return {
                "status": "available",
                "message": "Ollama服务正常运行",
                "endpoint": self.endpoint
            }
        except Exception as e:
            error_message = str(e)
            logger.warning(f"Ollama服务不可用: {error_message}")
            
            # 尝试提供更有用的错误信息
            suggestion = ""
            if "refused" in error_message.lower():
                suggestion = "请检查Ollama服务是否已启动，或确认配置的端点是否正确"
            elif "timeout" in error_message.lower():
                suggestion = "连接超时，请确认Ollama服务是否在运行，或网络是否正常"
            
            return {
                "status": "unavailable",
                "message": f"无法连接到Ollama服务: {error_message}. {suggestion}",
                "endpoint": self.endpoint
            }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=is_retryable_exception,
        before_sleep=lambda retry_state: logger.warning(
            f"Ollama API request failed (attempt {retry_state.attempt_number}/{retry_state.stop.stop_max_attempt}), retrying in {retry_state.next_action.sleep:.1f}s. Reason: {retry_state.outcome.exception()}"
        ),
        reraise=True
    )
    async def _make_request(self, endpoint: str, payload: Optional[Dict[str, Any]] = None, method: str = "POST") -> Dict[str, Any]:
        """Makes the HTTP request to Ollama API with retry logic."""
        api_url = f"{self.endpoint}{endpoint}"
        if not endpoint.startswith('/'):
            api_url = f"{self.endpoint}/{endpoint}"
        
        request_timeout = aiohttp.ClientTimeout(total=1800.0)  # 30 minutes total timeout
        logger.debug(f"Sending {method} request to Ollama endpoint: {api_url} with timeout: {request_timeout.total}s")
        
        if payload is None: # Ensure payload is a dict for POST/PUT etc. if not provided.
            payload = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                request_kwargs = {"timeout": request_timeout}
                if method.upper() in ["POST", "PUT", "PATCH"]:
                    request_kwargs["json"] = payload
                # For GET or other methods that might use query params, payload could be used for params if structured differently.
                # However, /api/tags (GET) does not need a payload or params.

                async with session.request(method.upper(), api_url, **request_kwargs) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ollama API Error: Status={response.status}, Response: '{error_text[:200]}...'")
                        raise APIResponseError(
                            provider_name=self.provider_name, 
                            status_code=response.status,
                            response_body={"error": error_text},
                            details=f"HTTP {response.status}"
                        )
                    
                    # For /api/tags, the response might be empty if no models, handle gracefully
                    if response.content_length == 0 and method.upper() == "GET" and endpoint == "/api/tags":
                        logger.info("Received empty response for /api/tags, likely no models available.")
                        return {"models": []} # Return a structure that get_available_models expects
                    
                    return await response.json()
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Ollama API连接错误: {str(e)}")
            raise APIConnectionError(
                message=f"连接失败: {str(e)}",
                provider_name=self.provider_name,
                details=str(e)
            )
        except aiohttp.ClientResponseError as e:
            logger.error(f"Ollama API响应错误: {str(e)}")
            raise APIResponseError(
                message=f"响应错误: {str(e)}", 
                provider_name=self.provider_name,
                status_code=e.status,
                response_body={"error": str(e)}
            )
        except asyncio.TimeoutError as e:
            logger.error(f"Ollama API请求超时")
            raise APITimeoutError(
                message="请求超时",
                provider_name=self.provider_name,
                timeout_seconds=request_timeout.total
            )
        except json.JSONDecodeError as e:
            logger.error(f"无法解析Ollama API响应为JSON: {e}")
            raise APIResponseFormatError(
                message=f"无效的JSON响应: {e}",
                provider_name=self.provider_name,
                response_body={"error": str(e)}
            )
        except Exception as e:
            logger.exception(f"Ollama API请求中发生未预期错误: {e}")
            raise APIError(
                message=f"API请求失败: {str(e)}",
                provider_name=self.provider_name,
                details=str(e)
            )

    async def test_connection(self, model: Optional[str] = None) -> Dict[str, Any]:
        """Tests the connection to the Ollama service and optionally a specific model."""
        logger.info(f"Testing connection for Ollama provider at {self.endpoint}...")
        
        # 1. Basic connection test (check if service is reachable)
        try:
            # Use a lightweight endpoint like /api/version or just /
            async with aiohttp.ClientSession() as session:
                # Set a short timeout for basic connectivity check
                test_timeout = aiohttp.ClientTimeout(total=5.0) 
                async with session.get(f"{self.endpoint}/", timeout=test_timeout) as response:
                    # Allow 404 for base URL, but other errors indicate issues
                    if response.status != 200 and response.status != 404:
                        error_text = await response.text()
                        logger.warning(f"Ollama base endpoint check failed: Status {response.status}, Response: {error_text[:100]}...")
                        return {
                            "status": "error",
                            "message": f"无法访问 Ollama 服务 (状态码: {response.status})",
                            "error_details": error_text[:200] # Limit error detail length
                        }
            logger.info("Ollama base endpoint connectivity successful.")
            base_connection_ok = True
            base_message = "Ollama 服务可访问。"

        except aiohttp.ClientConnectorError as e:
            logger.error(f"Ollama connection error: {e}")
            return {"status": "error", "message": f"无法连接到 Ollama 地址: {self.endpoint} ({e})", "error_details": str(e)}
        except asyncio.TimeoutError:
            logger.error(f"Ollama connection timed out ({test_timeout.total}s)")
            return {"status": "error", "message": f"连接 Ollama 服务超时 ({test_timeout.total}s)", "error_details": "Timeout"}
        except Exception as e:
            logger.error(f"Error during Ollama connection test: {e}", exc_info=True)
            return {"status": "error", "message": f"测试连接时发生意外错误: {e}", "error_details": str(e)}

        # 2. If a model is specified, try to get model info (optional but good check)
        if model:
            logger.info(f"Additionally testing model: {model}")
            try:
                # This uses the existing _make_request with its own retry/timeout
                model_info = await self._make_request("/api/show", {"name": model})
                if model_info: # Check if response is not empty
                    logger.info(f"Successfully retrieved info for model '{model}'.")
                    # Return success including model info
                    return {
                        "status": "success",
                        "message": f"成功连接到 Ollama 并找到模型 '{model}'",
                        "response": f"成功连接到 Ollama 并找到模型 '{model}'" # Add simple response for frontend
                    }
                else:
                     # Should not happen if _make_request works, but handle defensively
                    logger.warning(f"Received empty response when checking model '{model}'.")
                    return {
                        "status": "warning", # Or error? Warning seems appropriate
                        "message": f"连接成功，但检查模型 '{model}' 时收到空响应",
                        "error_details": "Empty response from /api/show"
                    }
            except APIResponseError as e:
                # Specific error from _make_request (e.g., model not found 404)
                logger.warning(f"Failed to get info for model '{model}': {e}")
                # Check if it was a 404 model not found error
                if e.status_code == 404:
                     return {
                         "status": "error",
                         "message": f"Ollama 服务连接成功，但模型 '{model}' 未找到",
                         "error_details": str(e)
                     }
                else:
                    # Other API error
                    return {
                        "status": "error",
                        "message": f"检查模型 '{model}' 时出错",
                        "error_details": str(e)
                    }
            except Exception as e:
                # Catch potential APIConnectionError, APITimeoutError from _make_request
                logger.error(f"Error checking model '{model}': {e}", exc_info=True)
                return {
                    "status": "error",
                    "message": f"检查模型 '{model}' 时发生错误",
                    "error_details": str(e)
                }
        else:
            # If no model specified, basic connection success is enough
            return {
                "status": "success", 
                "message": base_message, 
                "response": base_message # Add simple response for frontend
            }

    async def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Generate text using Ollama API."""
        target_model = (model or self.default_model or "").strip()
        if not target_model:
            raise ConfigurationError(f"No model specified and no default_model configured for {self.provider_name}.")

        # 1. Start with hardcoded defaults
        final_params = self.default_api_params.copy()

        # 2. Check and apply environment variable defaults
        default_temp_str = os.environ.get('OLLAMA_TEMPERATURE')
        if default_temp_str:
            try:
                final_params['temperature'] = float(default_temp_str)
                logger.debug(f"Using default temperature from env: {final_params['temperature']}")
            except ValueError:
                logger.warning(f"Invalid OLLAMA_TEMPERATURE in env: '{default_temp_str}'. Using hardcoded default or kwargs.")

        default_tokens_str = os.environ.get('OLLAMA_MAX_TOKENS')
        if default_tokens_str:
            try:
                # Ollama's num_predict corresponds to max_tokens
                final_params['num_predict'] = int(default_tokens_str)
                logger.debug(f"Using max_tokens (num_predict) from env: {final_params['num_predict']}")
            except ValueError:
                logger.warning(f"Invalid OLLAMA_MAX_TOKENS in env: '{default_tokens_str}'. Using hardcoded default or kwargs.")

        # 3. Apply kwargs, overriding defaults and env vars
        final_params.update(kwargs)
            
        request_payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {} # Use 'options' for parameters like temperature, num_predict, top_p, top_k
        }
        
        # Add allowed API parameters to the 'options' field
        # Ollama API parameters: https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-completion
        valid_options = [
            "num_keep", "seed", "num_predict", "top_k", "top_p", 
            "tfs_z", "typical_p", "repeat_last_n", "temperature", 
            "repeat_penalty", "presence_penalty", "frequency_penalty",
            "mirostat", "mirostat_tau", "mirostat_eta", "penalize_newline",
            "stop", "numa", "num_ctx", "num_batch", "num_gpu", "main_gpu",
            "low_vram", "f16_kv", "vocab_only", "use_mmap", "use_mlock",
            "num_thread"
        ]
        for param, value in final_params.items():
            # Handle max_tokens mapping to num_predict if passed via kwargs
            if param == 'max_tokens' and 'num_predict' not in final_params:
                 param = 'num_predict'
                 
            if param in valid_options and value is not None: # Check for None
                request_payload["options"][param] = value
                
        logger.info(f"Calling Ollama API: Model='{target_model}', Endpoint='{self.endpoint}'")
        logger.debug(f"Ollama API effective options: { request_payload['options'] }")

        try:
            result = await self._make_request("/api/generate", request_payload)
            logger.debug(f"收到来自 Ollama /api/generate 的原始响应: {str(result)[:500]}...") # Log raw response
            
            if "response" in result:
                response_content = result["response"].strip()
                logger.info(f"Ollama 生成内容: '{response_content[:100]}...'") # Log extracted content
                return response_content # Return the stripped content
            
            if "error" in result:
                error_msg = result["error"]
                logger.error(f"Ollama API returned an error: {error_msg}")
                raise APIResponseError(self.provider_name, details=error_msg)
                
            unknown_format_msg = f"Unknown response format from Ollama. Preview: {str(result)[:200]}..."
            logger.error(unknown_format_msg)
            raise APIResponseError(self.provider_name, details=unknown_format_msg)

        except RetryError as e:
            logger.critical(f"Ollama API request failed after multiple retries: {e}")
            raise APIConnectionError(self.provider_name, details=f"API request failed after retries: {e}") from e

    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """
        Implement the abstract method 'generate' from BaseAPIHandler.
        
        This method delegates to generate_text to maintain the same behavior.
        
        Args:
            prompt: The input text prompt
            model: Model name, if not specified use default model
            **kwargs: Additional API parameters that override default parameters
            
        Returns:
            Generated text string response
        """
        return await self.generate_text(prompt, model, **kwargs)

    async def stream_chat(self, messages: List[Any], model: Optional[str] = None, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat responses from Ollama.
        Args:
            messages: List of conversation messages
            model: Model to use, defaults to self.default_model
            **kwargs: Additional parameters like temperature, etc.
            
        Yields:
            Streaming response chunks compatible with OpenAI format
        """
        # 1. Prepare model and parameters
        target_model = (model or self.default_model or "").strip()
        if not target_model:
            logger.error("No model specified for Ollama streaming and no default_model configured")
            raise ConfigurationError(f"No model specified and no default_model configured for {self.provider_name}.")
            
        # Merge parameters with defaults
        temperature = kwargs.get('temperature', self.default_api_params.get('temperature', 0.7))
        
        # 从默认参数和环境变量中获取max_tokens的值
        max_tokens = kwargs.get('max_tokens', self.default_api_params.get('max_tokens', 16000))
        logger.debug(f"Stream chat使用的max_tokens值: {max_tokens}")
    
        # 2. 将ChatMessage对象转换为dict
        formatted_messages = []
        for msg in messages:
            if hasattr(msg, 'dict') and callable(getattr(msg, 'dict')):
                # 如果是Pydantic模型或有dict方法的对象
                formatted_messages.append(msg.dict())
            elif hasattr(msg, 'model_dump') and callable(getattr(msg, 'model_dump')):
                # 如果是Pydantic v2模型
                formatted_messages.append(msg.model_dump())
            elif isinstance(msg, dict):
                # 如果已经是字典
                formatted_messages.append({
                    "role": msg.get("role", ""),
                    "content": msg.get("content", "")
                })
            else:
                # 其他情况，尝试直接获取属性
                formatted_messages.append({
                    "role": getattr(msg, "role", ""),
                    "content": getattr(msg, "content", "")
                })
                
        # 3. 转换为Ollama格式
        ollama_messages = self._filter_messages(formatted_messages)
        
        # 4. 准备请求体
        payload = {
            "model": target_model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        }
        
        # 5. 构建完整的API URL
        api_url = f"{self.endpoint}/api/chat"
        logger.debug(f"Ollama流式聊天URL: {api_url}")
        
        # 6. 发送请求并处理流式响应
        try:
            # 首先返回角色信息
            yield {"choices": [{"delta": {"role": "assistant"}}]}
            
            async with aiohttp.ClientSession() as session:
                # 增加流式请求的超时时间，避免大模型响应超时
                # 连接超时: 10秒, 总请求超时: 10分钟
                timeout = aiohttp.ClientTimeout(total=600, connect=10)
                logger.debug(f"使用自定义超时设置: 连接超时={timeout.connect}秒, 总超时={timeout.total}秒")
                
                async with session.post(
                    api_url,
                    json=payload,
                    timeout=timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ollama流式API错误: {response.status}, {error_text}")
                        yield {"error": f"Ollama API错误: HTTP {response.status}"}
                        return
                    
                    logger.debug(f"收到HTTP 200响应，开始处理流数据")
                    # 处理流式响应
                    chunk_count = 0 # 添加计数器
                    async for line in response.content:
                        chunk_count += 1
                        logger.debug(f"流块 #{chunk_count}: 收到原始字节串 (长度 {len(line)})")
                        if not line:
                             logger.debug(f"流块 #{chunk_count}: 空行，跳过")
                             continue
                            
                        line_str = line.decode('utf-8').strip()
                        logger.debug(f"流块 #{chunk_count}: 解码后的字符串: {line_str[:150]}...")
                        if not line_str:
                            logger.debug(f"流块 #{chunk_count}: 解码后为空字符串，跳过")
                            continue
                        
                        # logger.debug(f"收到原始流响应: {line_str[:100]}...") # 已被上面更详细的日志替代
                        
                        try:
                            logger.debug(f"流块 #{chunk_count}: 尝试解析JSON...")
                            data = json.loads(line_str)
                            logger.debug(f"流块 #{chunk_count}: JSON解析成功: {data}")
                            
                            # 检查错误
                            if "error" in data:
                                logger.error(f"Ollama API错误: {data['error']}")
                                yield {"error": data["error"]}
                                continue
                            
                            # 提取内容
                            if "message" in data and "content" in data["message"]:
                                content = data["message"]["content"]
                                
                                # 记录流式响应内容
                                logger.debug(f"流式响应内容: {content}")
                                
                                # 转换为OpenAI兼容格式
                                openai_format = {"choices": [{"delta": {"content": content}}]}
                                logger.debug(f"转换为OpenAI格式: {openai_format}")
                                
                                # 返回OpenAI兼容格式的内容块
                                yield openai_format
                            elif "done" in data and data["done"]:
                                # 处理完成消息
                                logger.debug(f"Ollama流式响应完成")
                                yield {"done": True}
                                continue
                            else:
                                logger.debug(f"意外的Ollama响应格式: {data}")
                                # 尝试从数据中提取有用信息
                                if isinstance(data, dict) and any(data.values()):
                                    for key, value in data.items():
                                        if isinstance(value, str) and value:
                                            logger.debug(f"尝试从键'{key}'提取内容: {value[:50]}...")
                                            yield {"choices": [{"delta": {"content": value}}]}
                                            break
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"流块 #{chunk_count}: 解析Ollama流式响应JSON时出错: {e}, 原始数据: {line_str[:100]}...")
                            # 如果解析失败且非空，尝试返回原始行
                            if line_str:
                                logger.warning(f"流块 #{chunk_count}: 由于JSON解析失败，将返回原始字符串作为内容")
                                yield {"choices": [{"delta": {"content": line_str}}]}
                                
                    logger.info(f"Ollama 响应流处理完成，共处理 {chunk_count} 个块")
                                
        except aiohttp.ClientError as e:
            logger.error(f"Ollama API连接错误: {str(e)}")
            yield {"error": f"Ollama API连接错误: {str(e)}"}
        finally:
            # 确保在任何情况下都发送完成标记 (即使循环异常退出)
            logger.info(f"Ollama stream_chat finally 块执行，发送完成标记")
            yield {"done": True}

    def _filter_messages(self, messages: List[Any]) -> List[Dict[str, str]]:
        """
        过滤消息，只保留受支持的消息类型，并转换为 Ollama 格式。
        Ollama API 支持 user 和 assistant 角色，以及 system 角色用于传递思考提示。
        
        支持两种输入格式:
        1. 字典列表: [{"role": "user", "content": "..."}, ...]
        2. Pydantic模型列表: 来自FastAPI路由的ChatMessage对象
        """
        logger.debug(f"_filter_messages 输入类型: {type(messages)}, 长度: {len(messages)}")
        filtered_messages = []
        
        for i, msg in enumerate(messages):
            logger.debug(f"处理消息 #{i}: 类型 = {type(msg)}")
            # 处理不同类型的消息对象
            role = None
            content = None
            
            if isinstance(msg, dict):
                # 字典格式
                logger.debug(f"消息 #{i} 是字典: 键 = {list(msg.keys())}")
                role = msg.get("role", "").lower()
                content = msg.get("content", "")
            else:
                # 假设是Pydantic模型对象(ChatMessage)或类似对象
                try:
                    logger.debug(f"消息 #{i} 是对象: 属性 = {dir(msg)}")
                    
                    # 首先尝试使用get方法
                    if hasattr(msg, "get") and callable(getattr(msg, "get")):
                        role = msg.get("role", "").lower()
                        content = msg.get("content", "")
                        logger.debug(f"使用get方法从对象提取: role = {role}, content = {content[:30] if content else ''}")
                    
                    # 如果get方法失败或未提取到值，尝试直接获取属性
                    if (not role or not content) and hasattr(msg, "role") and hasattr(msg, "content"):
                        role = getattr(msg, "role", "").lower()
                        content = getattr(msg, "content", "")
                        logger.debug(f"从对象属性提取: role = {role}, content = {content[:30] if content else ''}")
                    
                    # 尝试使用字典方法获取
                    if (not role or not content) and hasattr(msg, "dict") and callable(getattr(msg, "dict")):
                        msg_dict = msg.dict()
                        role = msg_dict.get("role", "").lower()
                        content = msg_dict.get("content", "")
                        logger.debug(f"从对象dict()中提取: role = {role}, content = {content[:30] if content else ''}")
                    
                    # 尝试使用model_dump方法获取 (Pydantic v2)
                    if (not role or not content) and hasattr(msg, "model_dump") and callable(getattr(msg, "model_dump")):
                        msg_dict = msg.model_dump()
                        role = msg_dict.get("role", "").lower()
                        content = msg_dict.get("content", "")
                        logger.debug(f"从对象model_dump()中提取: role = {role}, content = {content[:30] if content else ''}")
                    
                    # 尝试使用__dict__属性
                    if (not role or not content) and hasattr(msg, "__dict__"):
                        msg_dict = msg.__dict__
                        role = msg_dict.get("role", "").lower()
                        content = msg_dict.get("content", "")
                        logger.debug(f"从对象__dict__中提取: role = {role}, content = {content[:30] if content else ''}")
                    
                    if not role or not content:
                        logger.warning(f"无法从消息对象提取数据: 不支持的对象类型")
                        continue
                except Exception as e:
                    logger.error(f"无法从消息对象提取role和content: {e}")
                    continue
            
            # 添加系统、用户和助手消息
            if role in ["system", "user", "assistant"]:
                filtered_messages.append({"role": role, "content": content})
                logger.debug(f"添加过滤后的消息 #{i}: role = {role}, content_length = {len(content) if content else 0}")
            else:
                logger.warning(f"跳过不支持的消息角色: {role}")
                
        # 记录过滤后的消息列表
        logger.debug(f"过滤后的消息列表: {len(filtered_messages)} 条消息")
                
        return filtered_messages

    async def chat(self, messages: List[Any], model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Implement non-streaming chat functionality for Ollama.
        
        Args:
            messages: List of messages in format [{"role": "user", "content": "Hello"}, ...]
            model: Model name, if not specified use default model
            **kwargs: Additional API parameters that override default parameters
            
        Returns:
            Dictionary containing the response content and metadata
        """
        target_model = (model or self.default_model or "").strip()
        if not target_model:
            logger.error("Chat model not specified and cannot get default model")
            raise ConfigurationError(f"No model specified and no default model configured for {self.provider_name}.")
        
        # 1. Start with hardcoded defaults
        final_params = self.default_api_params.copy()

        # 2. Check and apply environment variable defaults
        default_temp_str = os.environ.get('OLLAMA_TEMPERATURE')
        if default_temp_str:
            try:
                final_params['temperature'] = float(default_temp_str)
                logger.debug(f"Using default temperature from env: {final_params['temperature']}")
            except ValueError:
                logger.warning(f"Invalid OLLAMA_TEMPERATURE in env: '{default_temp_str}'. Using hardcoded default or kwargs.")

        default_tokens_str = os.environ.get('OLLAMA_MAX_TOKENS')
        if default_tokens_str:
            try:
                # Ollama's num_predict corresponds to max_tokens
                final_params['num_predict'] = int(default_tokens_str)
                logger.debug(f"Using max_tokens (num_predict) from env: {final_params['num_predict']}")
            except ValueError:
                logger.warning(f"Invalid OLLAMA_MAX_TOKENS in env: '{default_tokens_str}'. Using hardcoded default or kwargs.")

        # 3. Apply kwargs, overriding defaults and env vars
        final_params.update(kwargs)
        
        # Filter messages
        logger.debug(f"过滤消息前: 消息数量={len(messages)}, 类型={type(messages)}")
        filtered_messages = self._filter_messages(messages)
        logger.debug(f"过滤消息后: 消息数量={len(filtered_messages)}")
                
        if not filtered_messages:
            logger.warning("所有消息都被过滤掉了，至少添加一条空的用户消息")
            filtered_messages = [{"role": "user", "content": "Hello"}]
        
        # 输出详细的消息列表日志，方便排障
        for i, msg in enumerate(filtered_messages):
            role = msg.get("role", "unknown")
            content_preview = msg.get("content", "")[:50] + ("..." if len(msg.get("content", "")) > 50 else "")
            logger.debug(f"过滤后消息 #{i}: role={role}, content={content_preview}")
        
        # Prepare request payload
        payload = {
            "model": target_model,
            "messages": filtered_messages,
            "stream": False,
            "options": {} # Use 'options'
        }
        
        # Add allowed API parameters to the 'options' field
        valid_options = [
            "num_keep", "seed", "num_predict", "top_k", "top_p", 
            "tfs_z", "typical_p", "repeat_last_n", "temperature", 
            "repeat_penalty", "presence_penalty", "frequency_penalty",
            "mirostat", "mirostat_tau", "mirostat_eta", "penalize_newline",
            "stop", "numa", "num_ctx", "num_batch", "num_gpu", "main_gpu",
            "low_vram", "f16_kv", "vocab_only", "use_mmap", "use_mlock",
            "num_thread"
        ]
        for param, value in final_params.items():
             # Handle max_tokens mapping to num_predict if passed via kwargs
            if param == 'max_tokens' and 'num_predict' not in final_params:
                 param = 'num_predict'
                 
            if param in valid_options and value is not None: # Check for None
                payload["options"][param] = value
        
        logger.info(f"Starting Ollama chat: model={target_model}, message count={len(filtered_messages)}")
        logger.debug(f"Ollama chat API effective options: {payload['options']}")
        
        # Make the API call
        try:
            result = await self._make_request("/api/chat", payload)
            
            if "message" in result and "content" in result["message"]:
                content = result["message"]["content"]
                # 返回标准格式的响应字典
                return {
                    "role": "assistant",
                    "content": content,
                    "model": target_model,
                    "provider": self.provider_name,
                    "usage": {
                        "prompt_tokens": 0,  # Ollama不提供精确的token计数
                        "completion_tokens": 0,
                        "total_tokens": 0
                    }
                }
            else:
                logger.error(f"Unexpected Ollama chat response format: {result}")
                raise APIResponseError(self.provider_name, details="Unexpected response format")
                
        except Exception as e:
            logger.error(f"Error in Ollama chat: {str(e)}")
            raise APIConnectionError(self.provider_name, details=str(e))

    def get_current_param(self, param_name, default=None):
        """从环境变量中读取当前参数值
        
        直接从.env文件读取最新配置，而不是使用缓存的环境变量
        
        Args:
            param_name (str): 参数名称
            default: 默认值，如果参数不存在
            
        Returns:
            参数值或默认值
        """
        # 获取项目根目录中的.env文件
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env')
        
        # 读取.env文件
        env_values = dotenv_values(env_path)
        
        # 尝试获取参数值，首先查找特定于提供商的参数
        provider_prefix = "OLLAMA_"
        provider_param = f"{provider_prefix}{param_name.upper()}"
        
        # 首先检查特定于提供商的参数
        if provider_param in env_values:
            return env_values[provider_param]
        
        # 然后检查通用参数
        if param_name in env_values:
            return env_values[param_name]
        
        # 最后返回默认值
        return default 