"""
Anyscale Endpoints API handler implementation (OpenAI Compatible).
"""
import json
import aiohttp
import asyncio
from typing import Optional, Dict, Any, List, AsyncGenerator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError

from src.utils.logging import logger
from src.providers.base import BaseAPIHandler
from src.validation.error_handler import ConfigurationError as ConfigError, APIError, APIResponseError, APIResponseFormatError, APIConnectionError, APITimeoutError
from src.utils.retry import is_retryable_exception

class AnyscaleEndpointsHandler(BaseAPIHandler):
    """Handles interaction with Anyscale Endpoints API (OpenAI Compatible)."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_name = config.get('provider_name', 'anyscale_endpoints')
        env_prefix = "ANYSCALE_"
        
        self.api_key = config.get(f"{env_prefix}API_KEY")
        self.endpoint = config.get(f"{env_prefix}ENDPOINT", 'https://api.endpoints.anyscale.com/v1')
        self.default_model = config.get(f"{env_prefix}DEFAULT_MODEL", 'mistralai/Mixtral-8x7B-Instruct-v0.1')
        self.default_api_params = {
            'temperature': config.get(f"{env_prefix}TEMPERATURE", 0.7),
            'top_p': config.get(f"{env_prefix}TOP_P", 1.0),
            'max_tokens': config.get(f"{env_prefix}MAX_TOKENS", 2048)
        }
        self.request_timeout = config.get(f"{env_prefix}REQUEST_TIMEOUT", 60)

        if not self.api_key:
            raise ConfigError(f"Provider '{self.provider_name}' is missing required '{env_prefix}API_KEY' configuration.")
        if not self.endpoint:
            raise ConfigError(f"Provider '{self.provider_name}' is missing required '{env_prefix}ENDPOINT' configuration.")

        if self.endpoint.endswith('/'):
            self.chat_endpoint = f"{self.endpoint}chat/completions"
            self.models_endpoint = f"{self.endpoint}models"
        else:
            self.chat_endpoint = f"{self.endpoint}/chat/completions"
            self.models_endpoint = f"{self.endpoint}/models"

        logger.info(f"Anyscale Endpoints Handler Initialized: Name='{self.provider_name}', Endpoint='{self.endpoint}', DefaultModel='{self.default_model}'")

    def get_required_config_fields(self) -> List[str]:
        env_prefix = "ANYSCALE_"
        return [f"{env_prefix}API_KEY", f"{env_prefix}ENDPOINT"]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=is_retryable_exception,
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"Anyscale models fetch failed (attempt {retry_state.attempt_number}), retrying. Reason: {retry_state.outcome.exception()}"
        )
    )
    async def get_available_models(self) -> List[str]:
        if not self.models_endpoint:
            logger.warning(f"Cannot fetch models for {self.provider_name}: Models endpoint not configured.")
            return [self.default_model] if self.default_model else []
            
        logger.info(f"Attempting to fetch Anyscale models from: {self.models_endpoint}")
        try:
            headers = self._get_headers()
            async with aiohttp.ClientSession() as session:
                async with session.get(self.models_endpoint, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    response_text = await response.text()
                    if response.status != 200:
                        logger.error(f"Anyscale Endpoints API error fetching models: {response.status}, {response_text[:200]}...")
                        try: response_json = json.loads(response_text)
                        except json.JSONDecodeError: response_json = {"error": response_text}
                        raise APIResponseError(message=f"Failed to fetch models: HTTP {response.status}", status_code=response.status, response_body=response_json, provider=self.provider_name)
                    
                    data = await response.json()
                    models = [str(model['id']) for model in data.get('data', []) if isinstance(model, dict) and 'id' in model]
                    logger.info(f"Available Anyscale Endpoints models: {models}")
                    return models
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Anyscale Endpoints API connection error fetching models: {e}")
            raise APIConnectionError(message=f"Connection error: {e}", detail=str(e), provider=self.provider_name) from e
        except asyncio.TimeoutError:
             logger.error(f"Timeout fetching Anyscale models from {self.models_endpoint}")
             raise APITimeoutError(message="Timeout fetching models", timeout_value=15, provider=self.provider_name)
        except json.JSONDecodeError as e:
             logger.error(f"Failed to decode JSON response from Anyscale models endpoint: {e}, Response: {response_text[:200]}...")
             raise APIResponseFormatError(message="Invalid JSON response from models endpoint", response_body={"raw_response": response_text}, provider=self.provider_name) from e
        except APIError as e:
             raise e
        except Exception as e:
            logger.error(f"Unexpected error getting Anyscale Endpoints models: {str(e)}", exc_info=True)
            raise APIError(message=f"Unexpected error getting models: {e}", provider=self.provider_name) from e

    def _get_headers(self) -> Dict[str, str]:
        if not self.api_key:
            env_prefix = "ANYSCALE_"
            raise ConfigError(f"API key ({env_prefix}API_KEY) is missing for {self.provider_name} headers.")
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
            f"Anyscale HTTP request failed (attempt {retry_state.attempt_number}), retrying. Reason: {retry_state.outcome.exception()}"
        )
    )
    async def _make_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.chat_endpoint:
            raise ConfigError(f"Chat endpoint not configured for {self.provider_name}")
            
        logger.debug(f"Sending request to Anyscale Endpoints endpoint: {self.chat_endpoint}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.chat_endpoint,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout)
                ) as response:
                    response_text = await response.text()
                    if response.status != 200:
                        logger.error(f"Anyscale Endpoints API HTTP error: status={response.status}, response: '{response_text[:200]}...'")
                        try: response_json = json.loads(response_text)
                        except json.JSONDecodeError: response_json = {"error": response_text}
                        raise APIResponseError(message=f"HTTP {response.status}", status_code=response.status, response_body=response_json, provider=self.provider_name)
                        
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to decode successful JSON response from Anyscale: {e}, Response: '{response_text[:200]}...'")
                        raise APIResponseFormatError(message="Invalid JSON in successful response", response_body={"raw_response": response_text}, provider=self.provider_name) from e
                        
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Anyscale Endpoints API connection error: {e} URL: {self.chat_endpoint}")
            raise APIConnectionError(message=f"Network connection error: {e}", detail=str(e), provider=self.provider_name) from e
        except asyncio.TimeoutError as e:
             logger.error(f"Anyscale Endpoints API request timeout ({self.request_timeout}s) URL: {self.chat_endpoint}")
             raise APITimeoutError(message=f"Request timed out after {self.request_timeout}s", timeout_value=self.request_timeout, provider=self.provider_name) from e
        except aiohttp.ClientError as e:
            logger.error(f"Anyscale Endpoints API request failed (aiohttp client error): {e} URL: {self.chat_endpoint}")
            raise APIError(message=f"API client error: {e}", detail=str(e), provider=self.provider_name) from e

    async def generate(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        return await self.generate_text(prompt, model, **kwargs)

    async def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        target_model = (model or self.default_model or "").strip()
        if not target_model:
            raise ConfigError(f"No model specified and no default model configured for {self.provider_name}")

        messages = [{"role": "user", "content": prompt}]
        
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
            "stream": False, 
        }
        valid_params = ["temperature", "top_p", "max_tokens", "frequency_penalty", "presence_penalty", "stop"]
        for param, value in final_api_params.items():
            if param in valid_params and value is not None:
                payload[param] = value

        logger.debug(f"Anyscale generate_text payload: { {k:v for k,v in payload.items() if k != 'messages'} }")
        try:
            result = await self._make_request(payload=payload)
            if "choices" in result and isinstance(result["choices"], list) and len(result["choices"]) > 0:
                # 兼容分片内容
                content = ""
                for choice in result["choices"]:
                    if "message" in choice and "content" in choice["message"]:
                        content += choice["message"]["content"]
                if content:
                    usage = result.get("usage")
                    if usage:
                        logger.info(f"Anyscale Endpoints API call successful. Usage: {usage}")
                    else:
                        logger.info("Anyscale Endpoints API call successful.")
                    return content.strip()
                    
            logger.warning(f"Anyscale Endpoints response format unexpected: {str(result)[:200]}...")
            raise APIResponseFormatError(message="Unexpected response format", response_body=result, provider=self.provider_name)
            
        except APIError as e:
             logger.error(f"Anyscale generate_text failed: {type(e).__name__} - {e}")
             raise e
        except RetryError as e:
            logger.critical(f"Anyscale Endpoints API request failed after retries: {e}")
            raise APIError(f"API request failed after retries: {e}", detail=str(e.last_attempt.exception()), provider=self.provider_name) from e
        except Exception as e:
             logger.exception(f"Unexpected error during Anyscale generate_text: {e}")
             raise APIError(f"Unexpected internal error: {e}", provider=self.provider_name) from e

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        target_model = (model or self.default_model or "").strip()
        if not target_model:
            raise ConfigError(f"No model specified and no default model configured for {self.provider_name}")

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
            "stream": True,
        }
        valid_params = ["temperature", "top_p", "max_tokens", "frequency_penalty", "presence_penalty", "stop"]
        for param, value in final_api_params.items():
            if param in valid_params and value is not None:
                payload[param] = value
                
        if not self.chat_endpoint:
             yield {"error": f"Chat endpoint not configured for {self.provider_name}"}
             return

        logger.debug(f"Anyscale stream_chat payload: { {k:v for k,v in payload.items() if k != 'messages'} }")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.chat_endpoint,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout * 5, connect=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Anyscale Endpoints Stream API error: {response.status}, {error_text[:200]}...")
                        raise APIResponseError(message=f"HTTP {response.status}", status_code=response.status, response_body={"error": error_text}, provider=self.provider_name)

                    async for line in response.content:
                        if not line:
                            continue
                        line_str = line.decode('utf-8').strip()
                        if not line_str:
                            continue
                        if line_str.startswith("data: "):
                            data_str = line_str[len("data: "):].strip()
                            if data_str == "[DONE]":
                                logger.info("Anyscale Endpoints Stream chat completed")
                                yield {"status": "done"}
                                break
                            try:
                                data = json.loads(data_str)
                                yield data 
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse Anyscale Endpoints stream chunk: {e}, data: '{data_str[:100]}...'")
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Anyscale stream connection error: {str(e)}", exc_info=True)
            raise APIConnectionError(message=f"Network error during streaming: {e}", detail=str(e), provider=self.provider_name) from e
        except asyncio.TimeoutError as e:
            logger.error(f"Anyscale stream timeout ({self.request_timeout*5}s)")
            raise APITimeoutError(message="Stream request timed out", timeout_value=self.request_timeout*5, provider=self.provider_name) from e
        except APIError as e:
             logger.error(f"Anyscale stream API error: {type(e).__name__} - {e}")
             raise e
        except Exception as e:
            logger.exception(f"Anyscale stream chat unexpected error: {str(e)}")
            raise APIError(f"Unexpected streaming error: {e}", provider=self.provider_name) from e
        finally:
             logger.info(f"Anyscale stream processing ended for {self.provider_name}.") 