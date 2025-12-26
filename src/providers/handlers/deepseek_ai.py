"""
Deepseek AI API handler implementation.
"""
import json
import aiohttp
import os
from typing import Optional, Dict, Any, List, AsyncGenerator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
import asyncio
from src.utils.logging import logger
from src.providers.base import BaseAPIHandler
from src.validation.error_handler import ConfigurationError as ConfigError, APIError, APIResponseError, APIResponseFormatError, APIConnectionError, APITimeoutError
from src.utils.retry import is_retryable_exception

class DeepseekAIHandler(BaseAPIHandler):
    """Handles interaction with Deepseek AI API."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_name = config.get('provider_name', 'deepseek_ai')
        
        self.api_key = config.get('DEEPSEEK_API_KEY')
        
        self.endpoint = config.get('DEEPSEEK_ENDPOINT', 'https://api.deepseek.com/v1')
        
        self.default_model = config.get('DEEPSEEK_DEFAULT_MODEL')
        
        self.default_api_params = {
            'temperature': config.get('DEEPSEEK_TEMPERATURE', 0.7),
            'top_p': config.get('DEEPSEEK_TOP_P', 1.0),
            'max_tokens': config.get('DEEPSEEK_MAX_TOKENS', 2000),
        }
        
        self.request_timeout = config.get('DEEPSEEK_REQUEST_TIMEOUT', 30)
        
        if self.endpoint and self.endpoint.endswith('/'):
            self.endpoint = self.endpoint.rstrip('/')

        logger.info(f"Deepseek AI Handler Initialized: Name='{self.provider_name}', Endpoint='{self.endpoint}', DefaultModel='{self.default_model}'")

    def get_required_config_fields(self) -> List[str]:
        """Get the list of required configuration fields (env var names)."""
        return ['DEEPSEEK_API_KEY', 'DEEPSEEK_ENDPOINT']

    async def get_available_models(self) -> List[str]:
        # Add log entry at the very beginning of the function
        logger.debug(f"Entering get_available_models for {self.provider_name}")
        """Fetch available models from the Deepseek API /models endpoint."""
        # Construct the endpoint URL for listing models
        # FIX: Always use /v1/models, regardless of the base self.endpoint setting for chat
        # models_list_endpoint = f"{self.endpoint.rstrip('/')}/models"
        base_url_for_models = self.endpoint.replace('/v1', '').rstrip('/') # Ensure base has no v1 and no trailing slash
        if not base_url_for_models.endswith('api.deepseek.com'):
            logger.warning(f"Deepseek base endpoint '{self.endpoint}' seems unusual. Attempting to construct /v1/models path anyway.")
            # Best guess if endpoint is unusual
            base_url_for_models = "https://api.deepseek.com"
            
        models_list_endpoint = f"{base_url_for_models}/v1/models"

        logger.info(f"Fetching Deepseek AI models from: {models_list_endpoint}")

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
                        logger.error(f"Deepseek AI API error fetching models: {response.status}, {error_text}")
                        raise APIResponseError(provider_name=self.provider_name, status_code=response.status, response_body={"error": error_text}, details=f"Failed to fetch models: HTTP {response.status}")
                    
                    # Log the raw response body before parsing
                    raw_response_text = await response.text()
                    logger.debug(f"Raw response from Deepseek /v1/models: {raw_response_text[:500]}...") # Log first 500 chars

                    # Now parse the logged text
                    data = json.loads(raw_response_text) 
                    models = [str(model['id']) for model in data.get('data', []) if 'id' in model] 
                    logger.info(f"Available Deepseek AI models parsed: {models}")
                    return models
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Deepseek AI API connection error fetching models: {e}")
            raise APIConnectionError(message=f"Connection error: {e}", detail=str(e), provider=self.provider_name) from e
        except asyncio.TimeoutError:
             logger.error(f"Timeout fetching Deepseek models from {models_list_endpoint}")
             raise APITimeoutError(message="Timeout fetching models", timeout_value=10, provider=self.provider_name)
        except json.JSONDecodeError as e:
             logger.error(f"Failed to decode JSON response from Deepseek models endpoint: {e}")
             raise APIResponseFormatError(message="Invalid JSON response from models endpoint", response_body={"error": str(e)}, provider=self.provider_name) from e
        except APIError as e:
             # Re-raise API errors directly
             raise e
        except Exception as e:
            logger.error(f"Unexpected error getting Deepseek AI models: {str(e)}", exc_info=True)
            logger.warning(f"Returning default model or empty list due to error fetching Deepseek models for {self.provider_name}")
            return []
            
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        if not self.api_key:
            raise ConfigError("API key (DEEPSEEK_API_KEY) is missing for DeepseekAIHandler headers.")
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=is_retryable_exception, 
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"DeepSeek AI HTTP request failed (attempt {retry_state.attempt_number}/{retry_state.stop.stop_max_attempt}), retrying in {retry_state.next_action.sleep:.1f}s. Reason: {retry_state.outcome.exception()}"
        )
    )
    async def _make_request(self, endpoint_path: str, payload: Dict[str, Any], method: str = "POST") -> Dict[str, Any]:
        """Make an HTTP request to the API with retry logic."""
        request_url = f"{self.endpoint}{endpoint_path if endpoint_path.startswith('/') else '/' + endpoint_path}"
        logger.debug(f"Sending {method} request to DeepSeek AI endpoint: {request_url}")
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
                        logger.error(f"DeepSeek AI API HTTP error: status={response.status}, response: '{response_text[:200]}...'")
                        try: response_json = json.loads(response_text)
                        except json.JSONDecodeError: response_json = {"error": response_text}
                        raise APIResponseError(provider_name=self.provider_name, status_code=response.status, response_body=response_json, details=f"HTTP {response.status}")

                    try: 
                        return json.loads(response_text)
                    except json.JSONDecodeError as e:
                         logger.error(f"Failed to decode successful JSON response from DeepSeek AI: {e}, Response: '{response_text[:200]}...'")
                         raise APIResponseFormatError(message="Invalid JSON in successful response", response_body={"raw_response": response_text}, provider=self.provider_name) from e

        except aiohttp.ClientConnectorError as e:
            logger.error(f"DeepSeek AI API connection error: {e} URL: {request_url}")
            raise APIConnectionError(message=f"Network connection error: {e}", detail=str(e), provider=self.provider_name) from e
        except asyncio.TimeoutError as e:
             logger.error(f"DeepSeek AI API request timeout ({self.request_timeout}s) URL: {request_url}")
             raise APITimeoutError(message=f"Request timed out after {self.request_timeout}s", timeout_value=self.request_timeout, provider=self.provider_name) from e
        except aiohttp.ClientError as e:
            logger.error(f"DeepSeek AI API request failed (aiohttp client error): {e} URL: {request_url}")
            raise APIError(message=f"API client error: {e}", detail=str(e), provider=self.provider_name) from e

    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        return await self.generate_text(prompt, model, **kwargs)
        
    async def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Generate text using the Chat Completions endpoint (non-streaming)."""
        target_model = model or self.default_model
        if not target_model:
            raise ConfigError(f"No model specified and no default_model configured for {self.provider_name}.")

        messages = [{"role": "user", "content": prompt}]
        
        temperature = self.get_current_param("temperature", "float", self.default_api_params.get("temperature"))
        max_tokens = self.get_current_param("max_tokens", "int", self.default_api_params.get("max_tokens"))
        top_p = self.get_current_param("top_p", "float", self.default_api_params.get("top_p"))
        
        final_api_params = {
             "temperature": temperature,
             "max_tokens": max_tokens,
             "top_p": top_p
        }
        final_api_params.update(kwargs)

        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False,
        }
        valid_params = ["temperature", "top_p", "max_tokens", "frequency_penalty", "presence_penalty", "stop"]
        for param, value in final_api_params.items():
            if param in valid_params and value is not None:
                 payload[param] = value
                 
        logger.info(f"Calling Deepseek API (generate_text): Model='{target_model}', Base Endpoint='{self.endpoint}'")
        logger.debug(f"Deepseek API effective params: { {k:v for k,v in payload.items() if k not in ['messages','model']} }")

        try:
            result = await self._make_request(endpoint_path="/chat/completions", payload=payload)

            if "choices" in result and isinstance(result["choices"], list) and len(result["choices"]) > 0:
                # 兼容分片内容
                content = ""
                for choice in result["choices"]:
                    if "message" in choice and "content" in choice["message"]:
                        content += choice["message"]["content"]
                if content:
                    usage = result.get("usage")
                    if usage:
                        logger.info(f"DeepSeek API call successful. Usage: {usage}")
                    else:
                        logger.info("DeepSeek API call successful.")
                    return content.strip()
            
            logger.error(f"Unexpected response format from Deepseek generate_text: {str(result)[:200]}...")
            raise APIResponseFormatError(message="Unexpected response format", response_body=result, provider=self.provider_name)

        except APIError as e:
             logger.error(f"Deepseek API generate_text failed: {type(e).__name__} - {e}")
             raise e
        except RetryError as e:
            logger.critical(f"DeepSeek AI API generate_text request failed after retries: {e}")
            raise APIError(f"API request failed after retries: {e}", detail=str(e.last_attempt.exception()), provider=self.provider_name) from e
        except Exception as e:
             logger.exception(f"Unexpected error during Deepseek generate_text: {e}")
             raise APIError(provider_name=self.provider_name, message=f"Unexpected internal error: {e}", details=str(e)) from e

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat responses from the API."""
        target_model = model or self.default_model
        if not target_model:
            raise ConfigError(f"No model specified and no default model configured for {self.provider_name}.")

        temperature = self.get_current_param("temperature", "float", self.default_api_params.get("temperature"))
        max_tokens = self.get_current_param("max_tokens", "int", self.default_api_params.get("max_tokens"))
        top_p = self.get_current_param("top_p", "float", self.default_api_params.get("top_p"))

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
                  
        logger.info(f"Starting Deepseek streaming chat: model={target_model}, message count={len(messages)}")
        logger.debug(f"Deepseek streaming chat parameters: { {k:v for k,v in payload.items() if k != 'messages'} }")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.endpoint}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Deepseek AI Stream chat error: {response.status}, {error_text}")
                        raise APIResponseError(
                            provider_name=self.provider_name,
                            status_code=response.status, 
                            response_body={"error": error_text},
                            details=f"Stream chat error: HTTP {response.status}"
                        )
                    
                    # Process the streaming response line by line
                    async for line in response.content:
                        if not line:
                            continue
                            
                        line = line.decode('utf-8').strip()
                        if not line or line == "data: [DONE]" or not line.startswith("data:"):
                            continue
                            
                        try:
                            data = json.loads(line[5:].strip())  # Strip the "data: " prefix
                            yield data
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to decode JSON from stream: {e}, line: {line}")
                            continue
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Deepseek AI Stream chat connection error: {e}")
            raise APIConnectionError(
                message=f"Connection error: {e}",
                provider_name=self.provider_name,
                details=str(e)
            )
        except asyncio.TimeoutError:
            logger.error(f"Deepseek AI Stream chat timeout after {self.request_timeout}s")
            raise APITimeoutError(
                message=f"Request timed out after {self.request_timeout}s",
                provider_name=self.provider_name,
                timeout_seconds=self.request_timeout
            )
        except Exception as e:
            logger.error(f"Unexpected error in Deepseek AI Stream chat: {e}")
            raise APIError(
                message=f"Unexpected streaming error: {e}",
                provider_name=self.provider_name,
                details=str(e)
            )
        finally:
             logger.info("Deepseek AI stream processing ended.")