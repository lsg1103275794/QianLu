"""
Volc Engine API handler implementation - **Using Standard HTTP Requests (No SDK)**
"""
import json
import aiohttp
import os
from typing import Optional, Dict, Any, List, AsyncGenerator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
import asyncio # Import asyncio for potential async SDK usage
import dotenv # Keep dotenv if used by base class or get_current_param

from src.utils.logging import logger
from src.providers.base import BaseAPIHandler
# Keep common error handlers
from src.validation.error_handler import ConfigurationError as ConfigError, APIConnectionError, APIResponseError, APIError, APIResponseFormatError, APITimeoutError
from src.utils.retry import is_retryable_exception

class VolcEngineHandler(BaseAPIHandler):
    """Handles interaction with Volc Engine API using standard HTTP requests."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # --- 修改：读取 .env 配置，类似 SiliconFlow --- 
        self.api_key = config.get('VOLC_API_KEY') 
        self.endpoint = config.get('VOLC_ENDPOINT') 
        self.default_model = config.get('VOLC_DEFAULT_MODEL') 
        
        # Default API params from .env
        self.default_api_params = {
            'temperature': config.get('VOLC_TEMPERATURE', 0.7), 
            'top_p': config.get('VOLC_TOP_P', 1.0), 
            'max_tokens': config.get('VOLC_MAX_TOKENS', 2000), 
        }
        
        # Timeout from .env or default - 优先使用 VOLC_ENGINE_REQUEST_TIMEOUT，回退到 VOLC_REQUEST_TIMEOUT
        engine_timeout = config.get('VOLC_ENGINE_REQUEST_TIMEOUT')
        request_timeout = config.get('VOLC_REQUEST_TIMEOUT', 60)
        
        # 确保超时值是整数类型
        if engine_timeout is not None:
            self.request_timeout = int(engine_timeout) if not isinstance(engine_timeout, int) else engine_timeout
        else:
            self.request_timeout = int(request_timeout) if not isinstance(request_timeout, int) else request_timeout
        
        logger.info(f"Volc Engine Handler timeout set to: {self.request_timeout}s") 

        # Validate required fields (API Key and Endpoint are essential now)
        if not self.api_key:
            raise ConfigError(f"Provider '{self.provider_name}' is missing required 'VOLC_API_KEY'.")
        if not self.endpoint:
            raise ConfigError(f"Provider '{self.provider_name}' is missing required 'VOLC_ENDPOINT'.")
        # Model might still be required depending on API behavior
        # if not self.default_model:
        #      logger.warning(f"Provider '{self.provider_name}' is missing 'VOLC_DEFAULT_MODEL'.")
             
        # Ensure endpoint format is correct
        if self.endpoint and self.endpoint.endswith('/'):
            self.endpoint = self.endpoint.rstrip('/')

        logger.info(f"Volc Engine Handler (HTTP) Initialized: Endpoint='{self.endpoint}', DefaultModel='{self.default_model or 'Not Set'}'")

    def get_required_config_fields(self) -> List[str]:
        """Get the list of required configuration fields for HTTP mode."""
        # --- 修改：返回 HTTP 模式所需的环境变量 --- 
        return ['VOLC_API_KEY', 'VOLC_ENDPOINT', 'VOLC_DEFAULT_MODEL'] 

    async def get_available_models(self) -> List[str]:
        """Get available models. Implement if Volc HTTP API provides a listing endpoint."""
        # TODO: Check Volc HTTP API docs for a models listing endpoint
        # If available, implement using _make_request similar to SiliconFlowHandler
        # Example structure:
        # models_list_endpoint = f"{self.endpoint.replace('/chat/completions', '')}/models" # Guessing endpoint
        # try:
        #     response = await self._make_request(models_list_endpoint, payload=None, method="GET")
        #     # Process response based on actual API structure
        #     models = [model['id'] for model in response.get('data', [])]
        #     return models
        # except Exception as e:
        #     logger.error(f"Error fetching Volc models via HTTP: {e}")
        
        logger.warning("VolcEngineHandler.get_available_models using fallback (HTTP mode). Returning default model if set.")
        if self.default_model:
            return [self.default_model]
        return []

    # --- 实现 HTTP 请求头 --- 
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests using Bearer token."""
        if not self.api_key:
             # This should ideally be caught by __init__ or _validate_config
             raise ConfigError("API key (VOLC_API_KEY) is missing for VolcEngineHandler headers.")
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}' 
        }

    # --- 实现 HTTP 请求方法 (类似 SiliconFlow) --- 
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=is_retryable_exception,
        before_sleep=lambda retry_state: logger.warning(
            f"Volc Engine HTTP request failed (attempt {retry_state.attempt_number}/{retry_state.stop.stop_max_attempt}), retrying in {retry_state.next_action.sleep:.1f}s. Reason: {retry_state.outcome.exception()}"
        ),
        reraise=True
    )
    async def _make_request(self, endpoint_url: str, payload: Optional[Dict[str, Any]], method: str = "POST") -> Dict[str, Any]:
        """Make an HTTP request to the Volc Engine API with retries."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    endpoint_url,
                    headers=self._get_headers(),
                    json=payload if method == "POST" else None,
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout)
                ) as response:
                    response_text = await response.text()
                    
                    if response.status != 200:
                        logger.error(f"Volc Engine HTTP Error: Status={response.status}, Response: '{response_text[:200]}...' URL: {endpoint_url}")
                        try:
                            response_json = json.loads(response_text)
                        except json.JSONDecodeError:
                            response_json = {"error": response_text}
                            
                        raise APIResponseError(
                            provider_name=self.provider_name,
                            status_code=response.status,
                            response_body=response_json,
                            details=f"HTTP Error {response.status}"
                        )
                        
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError as e:
                        logger.error(f"Volc Engine HTTP Invalid JSON: {e}, Response Text: '{response_text[:200]}...' URL: {endpoint_url}")
                        raise APIResponseFormatError(
                            message="Invalid JSON in response",
                            provider_name=self.provider_name,
                            response_body={"raw_response": response_text}
                        )
                
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Volc Engine HTTP Connection Error: {e} URL: {endpoint_url}")
            raise APIConnectionError(
                message=f"Network connection error: {e}",
                provider_name=self.provider_name,
                details=str(e)
            )
        except asyncio.TimeoutError as e:
            logger.error(f"Volc Engine HTTP Request Timeout ({self.request_timeout}s) URL: {endpoint_url}")
            raise APITimeoutError(
                message=f"Request timed out after {self.request_timeout}s",
                provider_name=self.provider_name,
                timeout_seconds=self.request_timeout
            )
        except aiohttp.ClientError as e:
            logger.error(f"Volc Engine HTTP Request Failed (aiohttp Client Error): {e} URL: {endpoint_url}")
            raise APIError(
                message=f"API client error: {e}",
                provider_name=self.provider_name,
                details=str(e)
            )

    # --- 重写 generate_text 使用 HTTP 请求 --- 
    async def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Generate text using Volc Engine HTTP API."""
        target_model = (model or self.default_model or "").strip()
        if not target_model:
            raise ConfigError(f"No model specified and no default_model configured for {self.provider_name}.")

        # Use get_current_param to read real-time .env values
        temperature = self.get_current_param("temperature", "float", self.default_api_params.get("temperature"))
        max_tokens = self.get_current_param("max_tokens", "int", self.default_api_params.get("max_tokens"))
        top_p = self.get_current_param("top_p", "float", self.default_api_params.get("top_p"))

        # Build effective API params
        final_api_params = {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p
        }
        final_api_params.update(kwargs) 

        # Prepare payload in OpenAI compatible format (assuming Volc endpoint supports it)
        request_payload = {
            "model": target_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False 
        }
        
        # Add allowed API parameters 
        valid_params = ["temperature", "top_p", "max_tokens", "stop"] # Add other params Volc supports
        for param, value in final_api_params.items():
            if param in valid_params and value is not None: 
                request_payload[param] = value
                
        logger.info(f"Calling Volc Engine HTTP API (generate_text): Model='{target_model}', Endpoint='{self.endpoint}'")
        logger.debug(f"Volc Engine HTTP API effective params: { {k:v for k,v in request_payload.items() if k not in ['messages','model']} }")

        try:
            # Use the _make_request method with the configured endpoint
            result = await self._make_request(self.endpoint, request_payload)
            
            # Process successful response (assuming OpenAI compatible structure)
            if "choices" in result and isinstance(result["choices"], list) and len(result["choices"]) > 0:
                # 兼容分片内容
                content = ""
                for choice in result["choices"]:
                    if "message" in choice and "content" in choice["message"]:
                        content += choice["message"]["content"]
                if content:
                    usage = result.get("usage")
                    if usage:
                        logger.info(f"Volc Engine HTTP API call successful. Usage: {usage}")
                    else:
                        logger.info("Volc Engine HTTP API call successful.")
                    return content.strip()
            
            # Handle unexpected success format
            unknown_format_msg = f"Unknown success response format from Volc Engine HTTP. Preview: {str(result)[:200]}..."
            logger.error(unknown_format_msg)
            raise APIResponseFormatError(
                message="Unknown success response format", 
                provider_name=self.provider_name,
                response_body=result
            )

        except APIError as e:
            logger.error(f"Volc Engine HTTP API generate_text failed: {type(e).__name__} - {e}")
            raise e
        except RetryError as e:
            logger.critical(f"Volc Engine HTTP API generate_text failed after multiple retries: {e}")
            raise APIError(
                message=f"API request failed after retries: {e}",
                provider_name=self.provider_name,
                details=str(e.last_attempt.exception())
            ) from e
        except Exception as e:
             logger.exception(f"Unexpected error during Volc Engine HTTP generate_text: {e}")
             raise APIError(
                 message=f"Unexpected internal error: {e}",
                 provider_name=self.provider_name,
                 details=str(e)
             ) from e

    # --- generate (sync wrapper) remains the same --- 
    def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Synchronous wrapper for generate_text."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self.generate_text(prompt, model, **kwargs),
                    loop
                )
                return future.result(timeout=self.request_timeout + 5)
            else:
                return loop.run_until_complete(self.generate_text(prompt, model, **kwargs))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.generate_text(prompt, model, **kwargs))
            finally:
                loop.close()
                asyncio.set_event_loop(None)

    # --- 重写 stream_chat 使用 HTTP 请求 --- 
    async def stream_chat(
        self, 
        messages: List[Dict[str, Any]], 
        model: Optional[str] = None, 
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Implement streaming chat functionality using Volc Engine HTTP API."""
        target_model = (model or self.default_model or "").strip()
        if not target_model:
            err_msg = f"No model specified and no default_model configured for {self.provider_name} streaming."
            logger.error(err_msg)
            raise ConfigError(err_msg)

        # Use get_current_param for real-time values
        temperature = self.get_current_param("temperature", "float", self.default_api_params.get("temperature"))
        max_tokens = self.get_current_param("max_tokens", "int", self.default_api_params.get("max_tokens"))
        top_p = self.get_current_param("top_p", "float", self.default_api_params.get("top_p"))
        
        # Build effective API params
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

        # Prepare payload (assuming OpenAI compatible)
        request_payload = {
            "model": target_model,
            "messages": formatted_messages,
            "stream": True 
        }
        
        # Add allowed API parameters
        valid_params = ["temperature", "top_p", "max_tokens", "stop"] 
        for param, value in final_api_params.items():
            if param in valid_params and value is not None:
                request_payload[param] = value

        if not self.endpoint:
             raise ConfigError(f"Endpoint not configured for {self.provider_name}")
             
        request_url = self.endpoint # Use the main chat completions endpoint
        logger.info(f"Starting Volc Engine HTTP stream: Model='{target_model}', URL='{request_url}'")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    request_url,
                    headers=self._get_headers(),
                    json=request_payload,
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout, connect=30)
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Volc Engine HTTP Stream Error (HTTP {response.status}): {error_text[:200]}...")
                        raise APIResponseError(
                            provider_name=self.provider_name,
                            status_code=response.status,
                            response_body={"error": error_text},
                            details=f"Stream chat error: HTTP {response.status}"
                        )

                    # Process the stream (assuming Server-Sent Events like OpenAI)
                    async for line in response.content:
                        if line:
                            line_str = line.decode('utf-8').strip()
                            if line_str.startswith("data:"):
                                line_data = line_str[len("data:"):].strip()
                                if line_data == "[DONE]":
                                    logger.info("Volc Engine HTTP stream finished ([DONE] received).")
                                    yield {"status": "done"} 
                                    break 
                                try:
                                    chunk = json.loads(line_data)
                                    # Yield the chunk directly, assuming OpenAI compatible
                                    yield chunk 
                                except json.JSONDecodeError:
                                    logger.warning(f"Failed to decode Volc stream chunk JSON: {line_data}")

        except asyncio.TimeoutError:
             logger.error(f"Volc Engine HTTP stream timed out after {self.request_timeout}s. URL: {request_url}")
             raise APITimeoutError(
                 message=f"Stream request timed out after {self.request_timeout}s",
                 provider_name=self.provider_name,
                 timeout_seconds=self.request_timeout
             )
        except aiohttp.ClientError as e:
             logger.error(f"Volc Engine HTTP stream connection error: {e} URL: {request_url}")
             raise APIConnectionError(
                 message=f"Connection error: {e}",
                 provider_name=self.provider_name,
                 details=str(e)
             )
        except Exception as e:
             logger.exception(f"Unexpected error during Volc Engine HTTP stream: {e} URL: {request_url}")
             raise APIError(
                 message=f"Unexpected streaming error: {e}",
                 provider_name=self.provider_name,
                 details=str(e)
             )
        finally:
            logger.info(f"Volc Engine HTTP stream processing ended for Model='{target_model}'.")

# --- test_connection uses base class implementation --- 

# No more code below this line in the original snippet

# Ensure there's a newline or appropriate spacing before the next class/function if any
# ... (If there are subsequent definitions, ensure proper spacing) 