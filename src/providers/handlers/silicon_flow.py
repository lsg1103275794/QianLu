"""
Silicon Flow API handler implementation.
"""
import json
import aiohttp
import os
from typing import Optional, Dict, Any, List, AsyncGenerator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
import dotenv
import asyncio

from src.utils.logging import logger
from src.providers.base import BaseAPIHandler
from src.validation.error_handler import ConfigurationError as ConfigError, APIError, APIResponseError, APIResponseFormatError, APIConnectionError, APITimeoutError
from src.utils.retry import is_retryable_exception

class SiliconFlowHandler(BaseAPIHandler):
    """Handles interaction with Silicon Flow API."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_name = config.get('provider_name', 'silicon_flow')
        
        # --- 修正：直接从扁平的 config 字典获取带前缀的键 ---
        # credentials = config.get('credentials', {}) 
        # self.api_key = credentials.get('api_key')
        self.api_key = config.get('SILICONFLOW_API_KEY') # 从 .env 直接读取
        # -----------------------------------------------
        
        self.endpoint = config.get('SILICONFLOW_ENDPOINT', 'https://api.siliconflow.com/v1') 
        self.default_model = config.get('SILICONFLOW_DEFAULT_MODEL')
        
        self.default_api_params = {
            'temperature': config.get('SILICONFLOW_TEMPERATURE', 0.7),
            'top_p': config.get('SILICONFLOW_TOP_P', 1.0),
            'max_tokens': config.get('SILICONFLOW_MAX_TOKENS', 2000),
        }
        
        self.request_timeout = config.get('SILICONFLOW_REQUEST_TIMEOUT', 60)

        if self.endpoint and self.endpoint.endswith('/'):
            self.endpoint = self.endpoint.rstrip('/')

        logger.info(f"Silicon Flow Handler Initialized: Endpoint='{self.endpoint}', DefaultModel='{self.default_model}'")

    def get_required_config_fields(self) -> List[str]:
        """Get the list of required configuration fields (env var names)."""
        # 这个方法现在不再被 BaseAPIHandler 的 _validate_config 使用，
        # 但可以保留用于文档或未来的手动检查。
        return ['SILICONFLOW_API_KEY', 'SILICONFLOW_ENDPOINT']

    async def get_available_models(self) -> List[str]:
        """Get available models from the Silicon Flow API."""
        models_list_endpoint = f"{self.endpoint}/models"
        logger.info(f"Attempting to fetch SiliconFlow models from: {models_list_endpoint}")
        try:
            headers = self._get_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    models_list_endpoint,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Silicon Flow API error fetching models: {response.status}, {error_text}")
                        # 修改：使用更新的 APIError 构造函数
                        raise APIResponseError(
                            message=f"Failed to fetch models: HTTP {response.status}", 
                            status_code=response.status,
                            response_body={"error": error_text},
                            provider=self.provider_name
                        )
                    
                    data = await response.json()
                    # 确保模型 ID 是字符串
                    models = [str(model['id']) for model in data.get('data', []) if 'id' in model]
                    logger.info(f"Available Silicon Flow models: {models}")
                    return models
        except aiohttp.ClientError as e:
            logger.error(f"Silicon Flow API connection error fetching models: {e}")
            # 修改：使用更新的 APIConnectionError
            raise APIConnectionError(message=f"Connection error: {e}", detail=str(e), provider=self.provider_name) from e
        except json.JSONDecodeError as e:
             logger.error(f"Failed to decode JSON response from SiliconFlow models endpoint: {e}")
             raise APIResponseFormatError(message="Invalid JSON response from models endpoint", response_body={"error": str(e)}, provider=self.provider_name) from e
        except Exception as e: # Catch other potential errors
             logger.error(f"Unexpected error getting Silicon Flow models: {str(e)}", exc_info=True)
             # Consider re-raising as a generic APIError or returning empty list based on desired behavior
             raise APIError(message=f"Unexpected error getting models: {str(e)}", provider=self.provider_name) from e
             # return [self.default_model] if self.default_model else [] # Fallback to default or empty

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        # api_key 检查现在由 _validate_config 通过 get_required_config_fields 处理
        # if not self.api_key:
        #     raise ConfigError("API key is missing for SiliconFlowHandler headers.")
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=is_retryable_exception,
        before_sleep=lambda retry_state: logger.warning(
            f"SiliconFlow API request failed (attempt {retry_state.attempt_number}/{retry_state.stop.stop_max_attempt}), retrying in {retry_state.next_action.sleep:.1f}s. Reason: {retry_state.outcome.exception()}"
        ),
        reraise=True
    )
    async def _make_request(self, endpoint_path: str, payload: Dict[str, Any], method: str = "POST") -> Dict[str, Any]:
        """Make an HTTP request to the SiliconFlow API with retries."""
        if not self.endpoint:
            raise ConfigError(f"Endpoint not configured for {self.provider_name}")
            
        if not endpoint_path.startswith('/'):
            endpoint_path = '/' + endpoint_path
            
        request_url = f"{self.endpoint}{endpoint_path}"
        logger.debug(f"Sending {method} request to {self.provider_name} endpoint: {request_url}")
        
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
                        logger.error(f"SiliconFlow API HTTP error: {response.status}, {response_text[:200]}...")
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
                        logger.error(f"SiliconFlow API invalid JSON response: {e}")
                        raise APIResponseFormatError(
                            message="Invalid JSON in successful response",
                            provider_name=self.provider_name,
                            response_body={"raw_response": response_text[:500]}
                        )
                    
        except aiohttp.ClientConnectorError as e:
            logger.error(f"SiliconFlow API connection error: {e}")
            raise APIConnectionError(
                message=f"Connection error: {e}",
                provider_name=self.provider_name,
                details=str(e)
            )
        except asyncio.TimeoutError:
            logger.error(f"SiliconFlow API request timeout after {self.request_timeout}s")
            raise APITimeoutError(
                message=f"Request timed out after {self.request_timeout}s",
                provider_name=self.provider_name,
                timeout_seconds=self.request_timeout
            )
        except Exception as e:
            if isinstance(e, APIError):
                # Re-raise API errors with proper context
                raise e
            logger.error(f"SiliconFlow API request unexpected error: {e}")
            raise APIError(
                message=f"Unexpected error: {e}",
                provider_name=self.provider_name,
                details=str(e)
            )

    async def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Generate text using SiliconFlow API."""
        target_model = (model or self.default_model or "").strip()
        if not target_model:
            raise ConfigError(f"No model specified and no default_model configured for {self.provider_name}.")

        # --- 修改：使用 self.get_current_param 读取最新 .env 值 ---
        # temperature = self.default_api_params.get("temperature", 0.7)
        # max_tokens = self.default_api_params.get("max_tokens", 2000)
        # top_p = self.default_api_params.get("top_p", 1.0)
        
        # Read real-time parameters from .env using BaseAPIHandler's method
        # This ensures we use the absolute latest settings from the file
        temperature = self.get_current_param("temperature", "float", self.default_api_params.get("temperature"))
        max_tokens = self.get_current_param("max_tokens", "int", self.default_api_params.get("max_tokens"))
        top_p = self.get_current_param("top_p", "float", self.default_api_params.get("top_p"))

        # Build effective API params: start with real-time values, then override with kwargs
        final_api_params = {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p
        }
        final_api_params.update(kwargs) # Apply explicit kwargs over .env values

        request_payload = {
            "model": target_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False # Force non-streaming for this method
        }
        
        # Add allowed API parameters using the final_api_params
        valid_params = ["temperature", "top_p", "max_tokens", "presence_penalty", "frequency_penalty", "stop"]
        for param, value in final_api_params.items():
            if param in valid_params and value is not None: # Check for None explicitly
                request_payload[param] = value
                
        logger.info(f"Calling SiliconFlow API (generate_text): Model='{target_model}', Base Endpoint='{self.endpoint}'")
        logger.debug(f"SiliconFlow API effective params: { {k:v for k,v in request_payload.items() if k not in ['messages','model']} }")

        try:
            # Use the robust _make_request method
            result = await self._make_request("/chat/completions", request_payload)
            
            # Process successful response
            if "choices" in result and isinstance(result["choices"], list) and len(result["choices"]) > 0:
                first_choice = result["choices"][0]
                if "message" in first_choice and "content" in first_choice["message"]:
                    llm_output = first_choice["message"]["content"].strip()
                    usage = result.get("usage")
                    if usage:
                        logger.info(f"SiliconFlow API call successful. Usage: {usage}")
                    else:
                        logger.info("SiliconFlow API call successful.")
                    return llm_output
            
            # Handle cases where response structure is unexpected but status was 200
            unknown_format_msg = f"Unknown success response format from SiliconFlow. Preview: {str(result)[:200]}..."
            logger.error(unknown_format_msg)
            # Raise a format error instead of generic response error
            raise APIResponseFormatError(
                message="Unknown success response format", 
                provider_name=self.provider_name,
                response_body=result
            )

        # Catch specific errors raised by _make_request or BaseAPIHandler
        except APIError as e: # Catches APIResponseError, APIConnectionError etc.
            logger.error(f"SiliconFlow API generate_text failed: {type(e).__name__} - {e}")
            # Re-raise the specific error for the route handler to catch
            raise e
        except RetryError as e: # Specific handling for tenacity's RetryError
            logger.critical(f"SiliconFlow API generate_text failed after multiple retries: {e}")
            # Wrap in a generic APIError or a specific RetryFailedError if defined
            raise APIError(
                message=f"API request failed after retries: {e}", 
                provider_name=self.provider_name,
                details=str(e.last_attempt.exception())
            ) from e
        except Exception as e: # Catch any unexpected errors during processing
             logger.exception(f"Unexpected error during SiliconFlow generate_text: {e}")
             raise APIError(
                 message=f"Unexpected internal error: {e}", 
                 provider_name=self.provider_name,
                 details=str(e)
             ) from e

    def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """
        Synchronous wrapper for generate_text. Implements the abstract method required by BaseAPIHandler.
        
        Args:
            prompt: Text prompt to send to the model
            model: Model name to use, defaults to self.default_model
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            Generated text response
        """
        import asyncio
        
        # Create a new event loop if we're not in an async context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're already in an async context (e.g., FastAPI route)
                # Use run_coroutine_threadsafe for safety if called from a sync thread
                # logger.debug("generate() called within running event loop. Using run_coroutine_threadsafe.")
                future = asyncio.run_coroutine_threadsafe(
                    self.generate_text(prompt, model, **kwargs),
                    loop
                )
                # Add a timeout to prevent indefinite blocking
                return future.result(timeout=self.request_timeout + 5) # Add buffer to request timeout
            else:
                # We're in a sync context with an existing, non-running loop
                # logger.debug("generate() called with existing non-running loop. Using loop.run_until_complete.")
                return loop.run_until_complete(self.generate_text(prompt, model, **kwargs))
        except RuntimeError:
            # No event loop exists in the current thread
            # logger.debug("generate() called with no existing event loop. Creating new loop.")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.generate_text(prompt, model, **kwargs))
            finally:
                loop.close()
                asyncio.set_event_loop(None) # Clean up loop association
                
    async def stream_chat(
        self, 
        messages: List[Dict[str, Any]], 
        model: Optional[str] = None, 
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Implement streaming chat functionality for SiliconFlow.
        
        Args:
            messages: List of messages in format [{"role": "user", "content": "Hello"}, ...]
            model: Model name, if not specified use default model
            **kwargs: Additional API parameters that override default parameters
            
        Yields:
            Streaming output content fragments in OpenAI compatible format
            (e.g., {"choices": [{"delta": {"content": "...", "role": "assistant"}}]} or {"error": ...})
        """
        target_model = (model or self.default_model or "").strip()
        if not target_model:
            err_msg = f"No model specified and no default_model configured for {self.provider_name} streaming."
            logger.error(err_msg)
            yield {"error": err_msg}
            return

        # Use self.get_current_param to read real-time .env values
        temperature = self.get_current_param("temperature", "float", self.default_api_params.get("temperature"))
        max_tokens = self.get_current_param("max_tokens", "int", self.default_api_params.get("max_tokens"))
        top_p = self.get_current_param("top_p", "float", self.default_api_params.get("top_p"))
        
        # Build effective API params: start with real-time, override with kwargs
        final_api_params = {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p
        }
        final_api_params.update(kwargs) # Apply explicit kwargs

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

        request_payload = {
            "model": target_model,
            "messages": formatted_messages,
            "stream": True # Enable streaming
        }
        
        # Add allowed API parameters
        valid_params = ["temperature", "top_p", "max_tokens", "presence_penalty", "frequency_penalty", "stop"]
        for param, value in final_api_params.items():
            if param in valid_params and value is not None:
                request_payload[param] = value

        if not self.endpoint:
             yield {"error": "SiliconFlow Endpoint is not configured."}
             return
             
        request_url = f"{self.endpoint}/chat/completions"
        logger.info(f"Starting SiliconFlow stream: Model='{target_model}', URL='{request_url}'")
        # logger.debug(f"Stream Payload (excluding messages): { {k:v for k,v in request_payload.items() if k != 'messages'} }")

        try:
            # Note: Streaming requests typically shouldn't use tenacity retries in the same way
            # If the connection fails initially, a single retry might be ok, but not on chunks.
            # Consider adding a timeout for the initial connection phase.
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    request_url,
                    headers=self._get_headers(),
                    json=request_payload,
                    # Use a longer timeout for potentially long streams
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout * 5, connect=10) 
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"SiliconFlow Stream Error (HTTP {response.status}): {error_text[:200]}...")
                        # 修正错误处理，使用APIResponseError而不是直接yield错误
                        raise APIResponseError(
                            provider_name=self.provider_name,
                            status_code=response.status,
                            response_body={"error": error_text},
                            details=f"Stream chat error: HTTP {response.status}"
                        )

                    # Process the stream
                    async for line in response.content:
                        if line:
                            line_str = line.decode('utf-8').strip()
                            if line_str.startswith("data:"):
                                line_data = line_str[len("data:"):].strip()
                                if line_data == "[DONE]":
                                    logger.info("SiliconFlow stream finished ([DONE] received).")
                                    yield {"status": "done"} # Signal completion
                                    break # Exit the loop
                                try:
                                    chunk = json.loads(line_data)
                                    # Yield the chunk directly, assuming it's OpenAI compatible
                                    yield chunk 
                                except json.JSONDecodeError:
                                    logger.warning(f"Failed to decode stream chunk JSON: {line_data}")
                                    # Optionally yield an error chunk or just skip
                                    # yield {"warning": "Received invalid JSON chunk"}

        except asyncio.TimeoutError:
             logger.error(f"SiliconFlow stream timed out. URL: {request_url}")
             raise APITimeoutError(
                 message="Stream request timed out",
                 provider_name=self.provider_name,
                 timeout_seconds=self.request_timeout*5
             )
        except aiohttp.ClientError as e:
             logger.error(f"SiliconFlow stream connection error: {e} URL: {request_url}")
             raise APIConnectionError(
                 message=f"Connection error: {e}",
                 provider_name=self.provider_name,
                 details=str(e)
             )
        except Exception as e:
             logger.exception(f"Unexpected error during SiliconFlow stream: {e} URL: {request_url}")
             raise APIError(
                 message=f"Unexpected streaming error: {e}",
                 provider_name=self.provider_name,
                 details=str(e)
             )
        finally:
            logger.info(f"SiliconFlow stream processing ended for Model='{target_model}'.")

# --- Optional: Override test_connection if needed ---
#    If the default test_connection in BaseAPIHandler is insufficient (e.g., needs specific endpoint),
#    you can override it here. Otherwise, the base implementation will be used.
#
#    async def test_connection(self, model: Optional[str] = None) -> Dict[str, str]:
#        # Custom test logic, e.g., using the /models endpoint
#        try:
#            await self.get_available_models()
#            return {"status": "success", "message": f"Successfully listed models for {self.provider_name}."}
#        except APIError as e:
#            return {"status": "error", "message": f"Failed to list models: {str(e)}"}
#        except Exception as e:
#            return {"status": "error", "message": f"Unexpected error during test: {str(e)}"} 