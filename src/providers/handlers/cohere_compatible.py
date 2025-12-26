"""
Cohere API handler implementation (using OpenAI Compatible endpoint).
Note: Cohere has its own SDK, but this uses the compatible API layer.
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

class CohereCompatibleHandler(BaseAPIHandler):
    """Handles interaction with Cohere API via its OpenAI Compatible endpoint."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_name = config.get('provider_name', 'cohere_compatible')
        env_prefix = "COHERE_"
        
        self.api_key = config.get(f'{env_prefix}API_KEY')
        
        self.endpoint = config.get(f'{env_prefix}ENDPOINT', 'https://api.cohere.ai/v1') 
        
        self.default_model = config.get(f'{env_prefix}DEFAULT_MODEL', 'command-r-plus')
        
        self.request_timeout = config.get(f'{env_prefix}REQUEST_TIMEOUT', 60)
        
        self.default_api_params = {
            'temperature': config.get(f'{env_prefix}TEMPERATURE', 0.3), # Cohere default is lower
            'top_p': config.get(f'{env_prefix}TOP_P', 0.75),
            'max_tokens': config.get(f'{env_prefix}MAX_TOKENS', 2048)
            # Cohere specific params like 'k' might be passed via kwargs if needed
        }

        if self.endpoint and self.endpoint.endswith('/'):
            self.endpoint = self.endpoint.rstrip('/')

        logger.info(f"Cohere Compatible Handler Initialized: Name='{self.provider_name}', Endpoint='{self.endpoint}', DefaultModel='{self.default_model}'")

    def get_required_config_fields(self) -> List[str]:
        env_prefix = "COHERE_"
        return [f'{env_prefix}API_KEY', f'{env_prefix}ENDPOINT'] 

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        if not self.api_key:
            env_prefix = "COHERE_"
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
            f"Cohere models fetch failed (attempt {retry_state.attempt_number}), retrying. Reason: {retry_state.outcome.exception()}"
        )
    )
    async def get_available_models(self) -> List[str]:
        """Get available models from the API, falling back to known models."""
        logger.warning("Cohere model listing via OpenAI compatible API might be limited. Attempting /models fetch, fallback to known.")
        known_models = [
            "command-r-plus",
            "command-r",
            "command",
            "command-light",
        ]
        if self.default_model and self.default_model not in known_models:
             known_models.insert(0, self.default_model)
        
        if not self.endpoint:
             logger.warning(f"Cannot fetch models for {self.provider_name}: Endpoint not configured. Using known models.")
             return known_models
             
        models_endpoint_path = "/models"
        request_url = f"{self.endpoint}{models_endpoint_path}"
        logger.info(f"Attempting to fetch models from: {request_url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    request_url, 
                    headers=self._get_headers(), 
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_text = await response.text()
                    if response.status == 200:
                        data = await response.json()
                        api_models = [str(model['id']) for model in data.get('data', []) if isinstance(model, dict) and 'id' in model]
                        if api_models:
                           logger.info(f"Fetched models from Cohere /models endpoint: {api_models}")
                           combined = list(dict.fromkeys(known_models + api_models))
                           return combined
                        else:
                            logger.warning(f"Cohere /models endpoint returned 200 but no models found in expected format. Using known models.")
                    else:
                         logger.warning(f"Cohere /models endpoint returned status {response.status}: {response_text[:200]}. Using known models.")
                         # Don't raise error, just fallback

        except aiohttp.ClientConnectorError as e:
             logger.error(f"Network error fetching Cohere models via /models: {e}. Using known models.")
        except asyncio.TimeoutError:
             logger.error(f"Timeout fetching Cohere models via /models. Using known models.")
        except json.JSONDecodeError as e:
             logger.error(f"Failed to decode JSON response from Cohere models endpoint: {e}. Using known models.")
        except Exception as e:
            logger.error(f"Unexpected error fetching Cohere models via /models endpoint: {e}. Using known models.", exc_info=True)
            
        logger.info(f"Using known models for {self.provider_name}: {known_models}")
        return known_models

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=is_retryable_exception,
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"Cohere HTTP request failed (attempt {retry_state.attempt_number}), retrying. Reason: {retry_state.outcome.exception()}"
        )
    )
    async def _make_request(self, endpoint_path: str, payload: Dict[str, Any], method: str = "POST") -> Dict[str, Any]:
        """Make an HTTP request to the Cohere API with retry logic."""
        if not self.endpoint:
             raise ConfigError(f"Endpoint not configured for {self.provider_name}")
             
        if not endpoint_path.startswith('/'):
            endpoint_path = '/' + endpoint_path
        request_url = f"{self.endpoint}{endpoint_path}"
        logger.debug(f"Sending {method} request to Cohere compatible endpoint: {request_url}")
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
                        logger.error(f"Cohere Compatible API HTTP error: status={response.status}, response: '{response_text[:200]}...' for {self.provider_name}")
                        try: response_json = json.loads(response_text)
                        except json.JSONDecodeError: response_json = {"error": response_text}
                        raise APIResponseError(message=f"HTTP {response.status}", status_code=response.status, response_body=response_json, provider=self.provider_name)
                        
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError as e:
                         logger.error(f"Failed to decode successful JSON response from Cohere: {e}, Response: '{response_text[:200]}...'")
                         raise APIResponseFormatError(message="Invalid JSON in successful response", response_body={"raw_response": response_text}, provider=self.provider_name) from e
                         
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Cohere Compatible API connection error: {e} URL: {request_url}")
            raise APIConnectionError(message=f"Network connection error: {e}", detail=str(e), provider=self.provider_name) from e
        except asyncio.TimeoutError as e:
             logger.error(f"Cohere Compatible API request timeout ({self.request_timeout}s) URL: {request_url}")
             raise APITimeoutError(message=f"Request timed out after {self.request_timeout}s", timeout_value=self.request_timeout, provider=self.provider_name) from e
        except aiohttp.ClientError as e:
            logger.error(f"Cohere Compatible API request failed (aiohttp client error): {e} URL: {request_url}")
            raise APIError(message=f"API client error: {e}", detail=str(e), provider=self.provider_name) from e

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
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
        valid_params = ["temperature", "top_p", "max_tokens", "frequency_penalty", "presence_penalty", "stop", "k"] 
        for param, value in final_api_params.items():
            if param in valid_params and value is not None:
                payload[param] = value

        logger.debug(f"Generate payload for {self.provider_name}: { {k:v for k,v in payload.items() if k != 'messages'} }")

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
                        logger.info(f"Cohere Compatible API call successful. Usage: {usage}")
                    else:
                        logger.info("Cohere Compatible API call successful.")
                    return content.strip()
                    
            logger.warning(f"Cohere Compatible response format unexpected for {self.provider_name}: {str(result)[:200]}...")
            raise APIResponseFormatError(message="Unexpected response format", response_body=result, provider=self.provider_name)
            
        except APIError as e:
             logger.error(f"Cohere generate_text failed: {type(e).__name__} - {e}")
             raise e
        except RetryError as e:
            logger.critical(f"Cohere Compatible API request failed after retries for {self.provider_name}: {e}")
            raise APIError(f"API request failed after retries: {e}", detail=str(e.last_attempt.exception()), provider=self.provider_name) from e
        except Exception as e:
             logger.exception(f"Unexpected error during Cohere generate_text: {e}")
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
        valid_params = ["temperature", "top_p", "max_tokens", "frequency_penalty", "presence_penalty", "stop", "k"]
        for param, value in final_api_params.items():
            if param in valid_params and value is not None:
                payload[param] = value

        if not self.endpoint:
             yield {"error": f"Endpoint not configured for {self.provider_name}"}
             return
             
        logger.debug(f"Stream chat payload for {self.provider_name}: { {k:v for k,v in payload.items() if k != 'messages'} }")

        try:
            request_url = f"{self.endpoint}/chat/completions"
            logger.debug(f"Streaming request to: {request_url} for {self.provider_name}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    request_url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout * 5, connect=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Cohere Compatible Stream API error for {self.provider_name}: {response.status}, {error_text[:200]}...")
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
                                logger.info(f"Cohere Compatible Stream chat completed for {self.provider_name}")
                                yield {"status": "done"}
                                break
                            try:
                                data = json.loads(data_str)
                                yield data
                            except json.JSONDecodeError as e:
                                logger.warning(f"Failed to parse Cohere Compatible stream chunk for {self.provider_name}: {e}, data: '{data_str[:100]}...'")
                                
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Cohere Compatible stream chat connection error for {self.provider_name}: {str(e)}", exc_info=True)
            raise APIConnectionError(message=f"Network error during streaming: {e}", detail=str(e), provider=self.provider_name) from e
        except asyncio.TimeoutError as e:
            logger.error(f"Cohere Compatible stream chat timeout ({self.request_timeout*5}s) for {self.provider_name}")
            raise APITimeoutError(message="Stream request timed out", timeout_value=self.request_timeout*5, provider=self.provider_name) from e
        except APIError as e:
             logger.error(f"Cohere Compatible stream API error: {type(e).__name__} - {e}")
             raise e
        except Exception as e:
            logger.exception(f"Cohere Compatible stream chat unexpected error for {self.provider_name}: {str(e)}")
            raise APIError(f"Unexpected streaming error: {e}", provider=self.provider_name) from e
        finally:
             logger.info(f"Cohere stream processing ended for {self.provider_name}.") 