"""
Zhipu AI API handler implementation.
"""
import json
import time
import jwt
import aiohttp
import os
from typing import Optional, Dict, Any, List, AsyncGenerator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
import asyncio

from src.utils.logging import logger
from src.providers.base import BaseAPIHandler
from src.utils.error_handler import ConfigError, APIError, APIResponseError, APIConnectionError, APIResponseFormatError, APITimeoutError
from src.utils.retry import is_retryable_exception

class ZhipuAIHandler(BaseAPIHandler):
    """Handles interaction with Zhipu AI API."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # --- FIX: Set provider_name early --- 
        self.provider_name = config.get('provider_name', 'zhipu_ai')
        # -----------------------------------
        credentials = config.get('credentials', {})
        self.api_key = credentials.get('api_key')
        self.endpoint = config.get('endpoint', 'https://open.bigmodel.cn/api/paas/v4')
        self.default_model = config.get('default_model')
        
        self.default_api_params = {
            'temperature': config.get('temperature', 0.7),
            'top_p': config.get('top_p', 0.9),
            'max_tokens': config.get('max_tokens', 2000),
        }
        
        self.request_timeout = config.get('request_timeout', 60)

        if not self.api_key:
            # --- FIX: Use ConfigError --- 
            raise ConfigError(f"Provider '{self.provider_name}' is missing required 'api_key' in 'credentials'.")
            # -------------------------
        if not self.endpoint:
            # --- FIX: Use ConfigError --- 
             raise ConfigError(f"Provider '{self.provider_name}' is missing required 'endpoint'.")
             # -------------------------

        if self.endpoint.endswith('/'):
            self.endpoint = self.endpoint.rstrip('/')

        logger.info(f"Zhipu AI Handler Initialized: Endpoint='{self.endpoint}', DefaultModel='{self.default_model}'")

    def get_required_config_fields(self) -> List[str]:
        """Get the list of required configuration fields at the top level."""
        return ['credentials', 'endpoint']

    def _generate_jwt_token(self) -> str:
        """Generate JWT token for API authentication."""
        if not self.api_key:
            # --- FIX: Use ConfigError --- 
             raise ConfigError("Cannot generate JWT token without API key.")
             # -------------------------
        try:
            try:
                 id_part, secret_part = self.api_key.split('.')
            except ValueError:
                 # --- FIX: Use ConfigError --- 
                 raise ConfigError("Invalid Zhipu API Key format. Expected 'ID.Secret'.")
                 # -------------------------
                 
            payload = {
                "api_key": id_part,
                "exp": int(time.time()) + 3600,
                "timestamp": int(time.time())
            }
            
            token = jwt.encode(
                payload,
                secret_part,
                algorithm='HS256'
            )
            
            return token
            
        except Exception as e:
            logger.error(f"Failed to generate JWT token: {e}")
            # --- FIX: Use APIError --- 
            # raise APIConnectionError(self.provider_name, details=f"JWT token generation failed: {e}")
            raise APIError(f"JWT token generation failed: {e}", detail=str(e)) from e
            # -------------------------

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self._generate_jwt_token()}'
        }

    async def get_available_models(self) -> List[str]:
        """Get available models from the Zhipu AI API."""
        logger.warning("ZhipuAIHandler.get_available_models returning predefined list or default.")
        predefined_models = ["glm-4", "glm-3-turbo"]
        if self.default_model and self.default_model not in predefined_models:
             predefined_models.append(self.default_model)
        return predefined_models

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=is_retryable_exception,
        before_sleep=lambda retry_state: logger.warning(
            f"ZhipuAI API request failed (attempt {retry_state.attempt_number}/{retry_state.stop.stop_max_attempt}), retrying in {retry_state.next_action.sleep:.1f}s. Reason: {retry_state.outcome.exception()}"
        ),
        reraise=True
    )
    async def _make_request(self, endpoint_path: str, payload: Dict[str, Any], method: str = "POST") -> Dict[str, Any]:
        """Make a request to the ZhipuAI API with retries."""
        if not self.endpoint:
            raise ConfigError(f"Endpoint not configured for {self.provider_name}")
            
        request_url = f"{self.endpoint}{endpoint_path if endpoint_path.startswith('/') else '/' + endpoint_path}"
        logger.debug(f"Sending {method} request to ZhipuAI endpoint: {request_url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    request_url,
                    headers=self._get_headers(),
                    json=payload if method == "POST" else None,
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"ZhipuAI API HTTP error: {response.status}, {error_text[:200]}...")
                        try:
                            response_json = json.loads(error_text)
                        except json.JSONDecodeError:
                            response_json = {"error": error_text}
                            
                        raise APIResponseError(
                            provider_name=self.provider_name,
                            status_code=response.status,
                            response_body=response_json,
                            details=f"HTTP Error {response.status}"
                        )
                        
                    try:
                        return await response.json()
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to decode JSON response from ZhipuAI: {e}")
                        raise APIResponseFormatError(
                            message="Invalid JSON in response",
                            provider_name=self.provider_name,
                            response_body={"error": str(e)}
                        )
        except aiohttp.ClientConnectorError as e:
            logger.error(f"ZhipuAI API Request Failed (Network Error): {e}")
            raise APIConnectionError(
                message=f"Network connection error: {e}",
                provider_name=self.provider_name,
                details=str(e)
            )
        except asyncio.TimeoutError:
            logger.error(f"ZhipuAI API request timeout after {self.request_timeout}s")
            raise APITimeoutError(
                message=f"Request timed out after {self.request_timeout}s",
                provider_name=self.provider_name,
                timeout_seconds=self.request_timeout
            )
        except Exception as e:
            if isinstance(e, APIError):
                raise e
            logger.error(f"ZhipuAI API unexpected error: {e}")
            raise APIError(
                message=f"Unexpected error: {e}",
                provider_name=self.provider_name,
                details=str(e)
            )

    async def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Generate text using ZhipuAI API."""
        target_model = (model or self.default_model or "").strip()
        if not target_model:
            raise ConfigError(f"No model specified and no default model configured for {self.provider_name}")

        final_api_params = self.default_api_params.copy()
        final_api_params.update(kwargs)
            
        request_payload = {
            "model": target_model,
            "prompt": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": final_api_params.get("temperature"), 
            "top_p": final_api_params.get("top_p"),
            "max_tokens": final_api_params.get("max_tokens") 
        }
        
        request_payload = {k: v for k, v in request_payload.items() if v is not None}
        
        if 'temperature' in request_payload and not (0.0 < request_payload['temperature'] <= 1.0):
            logger.warning(f"Zhipu temperature {request_payload['temperature']} out of range (0, 1.0], adjusting to 0.95")
            request_payload['temperature'] = 0.95
        if 'top_p' in request_payload and request_payload['top_p'] >= 1.0:
             logger.warning(f"Zhipu top_p {request_payload['top_p']} >= 1.0, adjusting to 0.99")
             request_payload['top_p'] = 0.99
                
        logger.info(f"Calling ZhipuAI API: Model='{target_model}', Base Endpoint='{self.endpoint}'")
        logger.debug(f"ZhipuAI API effective params: { {k:v for k,v in request_payload.items() if k not in ['prompt','model']} }")

        try:
            result = await self._make_request("/chat/completions", request_payload)
            
            if "choices" in result and isinstance(result["choices"], list) and len(result["choices"]) > 0:
                # 兼容分片内容
                content = ""
                for choice in result["choices"]:
                    message = choice.get("message", choice.get("delta"))
                if message and isinstance(message, dict) and "content" in message:
                        content += message["content"]
                if content:
                    usage = result.get("usage")
                    if usage:
                        logger.info(f"ZhipuAI API call successful. Usage: {usage}")
                    else:
                        logger.info("ZhipuAI API call successful.")
                    return content.strip()
            
            if "error" in result:
                error_msg = result["error"].get("message", str(result["error"]))
                logger.error(f"ZhipuAI API returned an error: {error_msg}")
                raise APIResponseError(
                    message=error_msg, 
                    provider_name=self.provider_name,
                    response_body=result
                )
                
            unknown_format_msg = f"Unknown response format from ZhipuAI. Preview: {str(result)[:200]}..."
            logger.error(unknown_format_msg)
            raise APIResponseFormatError(
                message="Unknown response format", 
                provider_name=self.provider_name,
                response_body=result
            )

        except RetryError as e:
            logger.critical(f"ZhipuAI API request failed after multiple retries: {e}")
            raise APIError(
                message=f"API request failed after retries: {e}",
                provider_name=self.provider_name,
                details=str(e.last_attempt.exception()) if hasattr(e, 'last_attempt') else str(e)
            ) from e
        except Exception as e:
            if isinstance(e, APIError):
                raise e
            logger.exception(f"Unexpected error during ZhipuAI generate_text: {e}")
            raise APIError(
                message=f"Unexpected internal error: {e}",
                provider_name=self.provider_name,
                details=str(e)
            ) from e

    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """
        实现基类中的抽象方法 generate。调用 generate_text 方法实现文本生成功能。
        
        Args:
            prompt: 输入文本提示
            model: 模型名称，如未指定则使用默认模型
            **kwargs: 其他API参数，可覆盖默认参数
        
        Returns:
            生成的文本响应
        """
        return await self.generate_text(prompt, model, **kwargs)

    async def stream_chat(self, messages: List[Dict[str, Any]], model: Optional[str] = None, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Implement streaming chat functionality for ZhipuAI.
        
        Args:
            messages: List of messages in format [{"role": "user", "content": "Hello"}, ...]
            model: Model name, if not specified use default model
            **kwargs: Additional API parameters that override default parameters
            
        Yields:
            Streaming output content fragments in OpenAI compatible format
        """
        target_model = (model or self.default_model or "").strip()
        if not target_model:
            raise ConfigError(f"No model specified and no default model configured for {self.provider_name}")
        
        final_api_params = self.default_api_params.copy()

        # 3. Apply kwargs, overriding defaults and env vars
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
        
        # Prepare request body
        payload = {
            "model": target_model,
            "messages": formatted_messages,
            "stream": True,
            "temperature": final_api_params.get("temperature"),
            "top_p": final_api_params.get("top_p"),
            "max_tokens": final_api_params.get("max_tokens"),
            "request_id": final_api_params.get("request_id"),
            "incremental": True
        }
        
        payload = {k: v for k, v in payload.items() if v is not None}
        
        logger.info(f"Starting ZhipuAI streaming chat: model={target_model}, message count={len(messages)}")
        logger.debug(f"ZhipuAI streaming chat parameters: {payload}")
        
        try:
            # First return role information
            yield {"choices": [{"delta": {"role": "assistant"}}]}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.endpoint}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"ZhipuAI streaming API error: {response.status}, {error_text}")
                        raise APIResponseError(
                            provider_name=self.provider_name,
                            status_code=response.status,
                            response_body={"error": error_text},
                            details=f"Stream chat error: HTTP {response.status}"
                        )
                    
                    # Process streaming response
                    async for line in response.content:
                        if not line:
                            continue
                            
                        line_str = line.decode('utf-8').strip()
                        if not line_str:
                            continue
                            
                        if line_str.startswith("data: "):
                            data_str = line_str[6:].strip()
                            if data_str == "[DONE]":
                                logger.info("ZhipuAI streaming chat completed")
                                break
                                
                            try:
                                data = json.loads(data_str)
                                
                                # Check for errors
                                if "error" in data:
                                    logger.error(f"ZhipuAI API error: {data['error']}")
                                    raise APIError(
                                        message=f"Streaming error: {data['error']}",
                                        provider_name=self.provider_name,
                                        details=str(data['error'])
                                    )
                                
                                # Extract incremental content
                                if "choices" in data and len(data["choices"]) > 0:
                                    choice = data["choices"][0]
                                    if "delta" in choice:
                                        # Directly pass OpenAI compatible format
                                        yield data
                                
                            except json.JSONDecodeError as e:
                                logger.error(f"Error parsing ZhipuAI streaming response: {e}, Raw data: {data_str[:100]}...")
                                if data_str:
                                    yield {"choices": [{"delta": {"content": data_str}}]}
                                    
        except aiohttp.ClientConnectorError as e:
            logger.error(f"ZhipuAI stream chat network error: {str(e)}", exc_info=True)
            raise APIConnectionError(
                message=f"Connection error: {e}",
                provider_name=self.provider_name,
                details=str(e)
            )
        except asyncio.TimeoutError:
            logger.error(f"ZhipuAI stream chat timeout after {self.request_timeout}s")
            raise APITimeoutError(
                message="Stream request timed out",
                provider_name=self.provider_name,
                timeout_seconds=self.request_timeout
            )
        except Exception as e:
            if isinstance(e, APIError):
                raise e
            logger.error(f"Error in ZhipuAI streaming chat: {str(e)}", exc_info=True)
            raise APIError(
                message=f"Unexpected streaming error: {e}",
                provider_name=self.provider_name,
                details=str(e)
            ) 