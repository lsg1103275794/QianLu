"""
002 API handler (OpenAI-compatible).
"""
import json
import aiohttp
import asyncio # Add asyncio import
from typing import Optional, Dict, Any, List, AsyncGenerator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError

from src.utils.logging import logger
from src.providers.base import BaseAPIHandler
from src.validation.error_handler import ConfigurationError as ConfigError, APIError, APIResponseError, APIResponseFormatError, APIConnectionError, APITimeoutError
from src.utils.retry import is_retryable_exception

class 002Handler(BaseAPIHandler):
    """Template class for handling OpenAI-compatible API interactions.
    
    Note: This is an auto-generated handler for 002.
    When adding a new API, the system will automatically create a new handler class based on this template.
    **This template now expects flattened configuration based on environment variables.**
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # --- 修改：读取扁平化配置 --- 
        # Assume provider_name is passed correctly in config by factory
        self.provider_name = config.get('provider_name', '002') 
        
        # --- 关键：获取 ENV 前缀 (应由 Factory 保证元数据存在并传递) ---
        # 这个前缀是动态的，取决于具体实现的提供商
        # 模板代码无法硬编码，但实际 Handler 应能获取
        # 示例：env_prefix = config.get('env_prefix', self.provider_name.upper() + '_') 
        # 为了模板能运行，我们暂时用 provider_name 构造一个示例前缀
        # **实际使用时，应确保 factory.py 正确传递配置或元数据**
        env_prefix = self.provider_name.upper() + '_' # Example prefix
        logger.debug(f"[Template:{self.provider_name}] Using example ENV prefix: {env_prefix}")
        
        # credentials = config.get('credentials', {}) # Remove credentials logic
        # self.api_key = credentials.get('api_key')
        self.api_key = config.get(f'{env_prefix}API_KEY') # Use prefixed key
        
        # self.endpoint = config.get('endpoint') # Base URL like https://api.openai.com/v1
        # Provide a default only if the specific implementation doesn't require one in schema
        self.endpoint = config.get(f'{env_prefix}ENDPOINT') # Use prefixed key
        
        # self.default_model = config.get('default_model')
        self.default_model = config.get(f'{env_prefix}DEFAULT_MODEL') # Use prefixed key
        
        # self.request_timeout = config.get('request_timeout', 60)
        self.request_timeout = config.get(f'{env_prefix}REQUEST_TIMEOUT', 60) # Use prefixed key
        
        # --- 修改：从带前缀的配置读取 API 参数 --- 
        self.default_api_params = {
            'temperature': config.get(f'{env_prefix}TEMPERATURE', 0.7),
            'top_p': config.get(f'{env_prefix}TOP_P', 1.0),
            'max_tokens': config.get(f'{env_prefix}MAX_TOKENS', 2048)
        }

        # --- 移除旧的检查 --- 
        # if not self.endpoint:
        #     raise ConfigError(f"Provider '{self.provider_name}' Missing required configuration field: endpoint")
        # if not self.api_key:
        #     raise ConfigError(f"Provider '{self.provider_name}' Missing required configuration field: api_key in credentials")

        if self.endpoint and self.endpoint.endswith('/'):
            self.endpoint = self.endpoint.rstrip('/')

        logger.info(f"Template OpenAI Handler Initialized: Name='{self.provider_name}', Endpoint='{self.endpoint}', DefaultModel='{self.default_model}'")

    def get_required_config_fields(self) -> List[str]:
        """Get the list of required configuration fields (env var names).
           **Note:** Actual Handler should dynamically determine prefix.
        """
        # --- 修改：返回环境变量名称 --- 
        # return ['credentials', 'endpoint']
        # **重要:** 实际生成的 Handler 需要根据 providers_meta.json 中的 env_prefix 
        # 来动态生成这些必需字段的名称。
        # 例如: return [f'{self.provider_name.upper()}_API_KEY', f'{self.provider_name.upper()}_ENDPOINT']
        # 为了模板能通过基本检查，我们返回一个示例：
        env_prefix = self.provider_name.upper() + '_' # Example prefix
        return [f'{env_prefix}API_KEY', f'{env_prefix}ENDPOINT']

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        # (保持不变，已使用 self.api_key)
        if not self.api_key:
             # Use ConfigError from validation.error_handler
             env_prefix = self.provider_name.upper() + '_' # Example prefix
             raise ConfigError(f"API key ({env_prefix}API_KEY) is missing for {self.provider_name} headers.")
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

    async def get_available_models(self) -> List[str]:
        """Get available models from the API. (Assumes OpenAI /models endpoint)"""
        # (保持不变，但确保 self.endpoint 在 __init__ 中正确设置)
        if not self.endpoint:
             logger.warning(f"Cannot fetch models for {self.provider_name}: Endpoint not configured.")
             return [self.default_model] if self.default_model else []
             
        models_endpoint_path = "/models" 
        request_url = f"{self.endpoint}{models_endpoint_path}"
        logger.info(f"Attempting to fetch models from: {request_url} for provider {self.provider_name}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    request_url,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_text = await response.text()
                    if response.status != 200:
                        logger.error(f"API error fetching models from {request_url}: {response.status}, {response_text[:200]}...")
                        try: response_json = json.loads(response_text) 
                        except json.JSONDecodeError: response_json = {"error": response_text}
                        raise APIResponseError(
                            provider_name=self.provider_name,
                            status_code=response.status, 
                            response_body=response_json,
                            details=f"Failed to fetch models: HTTP {response.status}"
                        )
                    
                    data = await response.json()
                    models = [str(model['id']) for model in data.get('data', []) if 'id' in model]
                    logger.info(f"Available models for {self.provider_name}: {models}")
                    return models
        except APIError as e:
             raise e # Re-raise known API errors
        except Exception as e:
            logger.error(f"Error getting models for {self.provider_name}: {str(e)}", exc_info=True)
            if self.default_model:
                 logger.warning(f"Returning default model '{self.default_model}' due to error fetching model list.")
                 return [self.default_model]
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        # Use the updated retry logic and exception types
        retry=is_retryable_exception,
        reraise=True,
        # Call the instance method for logging
        before_sleep=lambda retry_state: logger.warning(
            f"[TemplateHandler] HTTP request failed (attempt {retry_state.attempt_number}/{retry_state.stop.stop_max_attempt}), retrying in {retry_state.next_action.sleep:.1f}s. Reason: {retry_state.outcome.exception()}"
        )
    )
    async def _make_request(self, endpoint_path: str, payload: Dict[str, Any], method: str = "POST") -> Dict[str, Any]:
        """Make an HTTP request to the API with retry logic."""
        # (保持不变，但确保 self.endpoint, self.request_timeout 在 __init__ 中正确设置)
        if not self.endpoint:
             raise ConfigError(f"Endpoint not configured for {self.provider_name}")
             
        if not endpoint_path.startswith('/'):
            endpoint_path = '/' + endpoint_path
        request_url = f"{self.endpoint}{endpoint_path}"
        logger.debug(f"Sending {method} request to endpoint: {request_url} for provider {self.provider_name}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    request_url,
                    headers=self._get_headers(), 
                    json=payload if method == "POST" else None,
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout) 
                ) as response:
                    response_text = await response.text()
                    if response.status != 200:
                        logger.error(f"API HTTP error: status={response.status}, response: '{response_text[:200]}...' for {self.provider_name}")
                        try: response_json = json.loads(response_text)
                        except json.JSONDecodeError: response_json = {"error": response_text}
                        raise APIResponseError(
                            provider_name=self.provider_name,
                            status_code=response.status, 
                            response_body=response_json,
                            details=f"HTTP {response.status}"
                        )

                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError as e:
                         logger.error(f"Failed to decode successful JSON response for {self.provider_name}: {e}, Response: '{response_text[:200]}...'")
                         raise APIResponseFormatError(
                             message="Invalid JSON in successful response", 
                             provider_name=self.provider_name,
                             response_body={"raw_response": response_text}
                         ) from e

        except aiohttp.ClientConnectorError as e:
            logger.error(f"API connection error for {self.provider_name}: {e} URL: {request_url}")
            raise APIConnectionError(
                message=f"Network connection error: {e}", 
                provider_name=self.provider_name,
                details=str(e)
            ) from e
        except asyncio.TimeoutError as e:
             logger.error(f"API request timeout ({self.request_timeout}s) for {self.provider_name} URL: {request_url}")
             raise APITimeoutError(
                 message=f"Request timed out after {self.request_timeout}s", 
                 provider_name=self.provider_name,
                 timeout_seconds=self.request_timeout
             ) from e
        except aiohttp.ClientError as e:
            logger.error(f"API request failed (aiohttp client error) for {self.provider_name}: {e} URL: {request_url}")
            raise APIError(
                message=f"API client error: {e}", 
                provider_name=self.provider_name,
                details=str(e)
            ) from e

    async def generate( self, prompt: str, model: Optional[str] = None, **kwargs ) -> str:
        # Use generate_text implementation
        return await self.generate_text(prompt, model, **kwargs)
        
    async def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Generate text using the Chat Completions endpoint (non-streaming)."""
        target_model = model or self.default_model
        if not target_model:
            raise ConfigError(f"Provider '{self.provider_name}' No model specified and no default model configured")

        # 确保消息是字典格式
        messages = [{"role": "user", "content": prompt}]
        
        # --- 修改：使用 get_current_param 读取最新参数 --- 
        # env_prefix = self.provider_name.upper() + '_' # Example prefix
        # temperature = self.default_api_params.get('temperature') # Old way
        temperature = self.get_current_param("temperature", "float", self.default_api_params.get('temperature'))
        max_tokens = self.get_current_param("max_tokens", "int", self.default_api_params.get('max_tokens'))
        top_p = self.get_current_param("top_p", "float", self.default_api_params.get('top_p'))
        
        final_api_params = {
             "temperature": temperature,
             "max_tokens": max_tokens,
             "top_p": top_p
        }
        final_api_params.update(kwargs)

        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False 
        }
        valid_params = ["temperature", "top_p", "max_tokens", "frequency_penalty", "presence_penalty", "stop"]
        for param, value in final_api_params.items():
            if param in valid_params and value is not None:
                payload[param] = value

        logger.debug(f"Generate payload for {self.provider_name}: { {k:v for k,v in payload.items() if k != 'messages'} }")

        try:
            result = await self._make_request(endpoint_path="/chat/completions", payload=payload)

            if "choices" in result and isinstance(result["choices"], list) and len(result["choices"]) > 0:
                first_choice = result["choices"][0]
                if "message" in first_choice and "content" in first_choice["message"]:
                    usage = result.get("usage")
                    if usage: logger.info(f"{self.provider_name} generate_text successful. Usage: {usage}")
                    else: logger.info(f"{self.provider_name} generate_text successful.")
                    return first_choice["message"]["content"].strip()

            logger.error(f"Unexpected response format from {self.provider_name} generate_text: {str(result)[:200]}...")
            raise APIResponseFormatError(
                message="Unexpected response format", 
                provider_name=self.provider_name,
                response_body=result
            )

        except APIError as e: 
             logger.error(f"{self.provider_name} generate_text failed: {type(e).__name__} - {e}")
             raise e
        except RetryError as e:
            logger.critical(f"API request failed after retries for {self.provider_name}: {e}")
            raise APIError(
                message=f"API request failed after retries: {e}", 
                provider_name=self.provider_name,
                details=str(e.last_attempt.exception())
            ) from e
        except Exception as e:
             logger.exception(f"Unexpected error during {self.provider_name} generate_text: {e}")
             raise APIError(
                 message=f"Unexpected internal error: {e}", 
                 provider_name=self.provider_name,
                 details=str(e)
             ) from e

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat responses from the API."""
        target_model = model or self.default_model
        if not target_model:
            raise ConfigError(f"Provider '{self.provider_name}' No model specified and no default model configured")

        # --- 修改：使用 get_current_param 读取最新参数 --- 
        temperature = self.get_current_param("temperature", "float", self.default_api_params.get('temperature'))
        max_tokens = self.get_current_param("max_tokens", "int", self.default_api_params.get('max_tokens'))
        top_p = self.get_current_param("top_p", "float", self.default_api_params.get('top_p'))

        final_api_params = {
             "temperature": temperature,
             "max_tokens": max_tokens,
             "top_p": top_p
        }
        final_api_params.update(kwargs)

        # 将ChatMessage对象转换为dict
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

        payload = {
            "model": target_model,
            "messages": formatted_messages,
            "stream": True,
        }
        valid_params = ["temperature", "top_p", "max_tokens", "frequency_penalty", "presence_penalty", "stop"]
        for param, value in final_api_params.items():
            if param in valid_params and value is not None:
                payload[param] = value

        logger.debug(f"Stream chat payload for {self.provider_name}: { {k:v for k,v in payload.items() if k != 'messages'} }")
        
        if not self.endpoint:
            yield {"error": f"Endpoint not configured for {self.provider_name}"}
            return

        try:
            # 不再需要 yield 初始 role
            # yield {"choices": [{"delta": {"role": "assistant"}}]}
            
            request_url = f"{self.endpoint}/chat/completions"
            logger.debug(f"Streaming request to: {request_url} for provider {self.provider_name}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post( 
                    request_url,
                    headers=self._get_headers(),
                    json=payload,
                    # Adjust timeout for streaming
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout * 5, connect=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Stream API error for {self.provider_name}: {response.status}, {error_text[:200]}...")
                        # 修正参数顺序
                        raise APIResponseError(
                            provider_name=self.provider_name,
                            status_code=response.status, 
                            response_body={"error": error_text},
                            details=f"Stream chat error: HTTP {response.status}"
                        )

                    async for line in response.content:
                        if not line:
                            continue

                        line_str = line.decode('utf-8').strip()
                        if not line_str:
                            continue

                        if line_str.startswith("data: "):
                            data_str = line_str[len("data: "):].strip()
                            if data_str == "[DONE]":
                                logger.info(f"Stream chat completed for {self.provider_name}")
                                yield {"status": "done"} # Yield completion marker
                                break

                            try:
                                data = json.loads(data_str)
                                # Yield OpenAI compatible chunks directly
                                yield data

                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse stream chunk for {self.provider_name}: {e}, Raw: {data_str[:100]}...")
                                # Optionally yield warning or skip

        # 修正异常处理中的参数顺序和字段名称
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Stream chat connection error for {self.provider_name}: {str(e)}", exc_info=True)
            raise APIConnectionError(
                message=f"Network error during streaming: {e}",
                provider_name=self.provider_name,
                details=str(e)
            )
        except asyncio.TimeoutError as e:
             logger.error(f"Stream chat timeout ({self.request_timeout*5}s) for {self.provider_name}")
             raise APITimeoutError(
                 message="Stream request timed out",
                 provider_name=self.provider_name,
                 timeout_seconds=self.request_timeout*5
             )
        except APIError as e:
             logger.error(f"Stream chat API error for {self.provider_name}: {type(e).__name__} - {e}")
             raise e
        except Exception as e:
            logger.exception(f"Stream chat unexpected error for {self.provider_name}: {str(e)}")
            raise APIError(
                message=f"Unexpected streaming error: {e}",
                provider_name=self.provider_name,
                details=str(e)
            )
        finally:
             logger.info(f"Stream processing ended for {self.provider_name}.") 