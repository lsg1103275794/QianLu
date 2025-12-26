"""
Together AI API handler implementation (OpenAI Compatible).
"""
import json
import aiohttp
from typing import Optional, Dict, Any, List, AsyncGenerator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError

from src.utils.logging import logger
from src.providers.base import BaseAPIHandler
from src.utils.error_handler import ConfigError, APIError, APIResponseError
from src.utils.retry import is_retryable_exception

class TogetherAiHandler(BaseAPIHandler):
    """Handles interaction with Together AI API (OpenAI Compatible)."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_name = config.get('provider_name', 'together_ai')
        self.api_key = config.get('api_key')
        self.endpoint = config.get('endpoint', 'https://api.together.xyz/v1') # Default Together endpoint
        self.default_model = config.get('default_model', 'mistralai/Mixtral-8x7B-Instruct-v0.1') 
        self.default_api_params = {
            'temperature': config.get('temperature', 0.7),
            'top_p': config.get('top_p', 0.7),
            'max_tokens': config.get('max_tokens', 512)
        }

        if not self.api_key:
            raise ConfigError(f"Provider '{self.provider_name}' is missing required 'api_key' configuration.")
        if not self.endpoint:
            raise ConfigError(f"Provider '{self.provider_name}' is missing required 'endpoint' configuration.")

        # Ensure endpoints are set correctly
        if self.endpoint.endswith('/'):
            self.chat_endpoint = f"{self.endpoint}chat/completions"
            self.models_endpoint = f"{self.endpoint}models"
        else:
            self.chat_endpoint = f"{self.endpoint}/chat/completions"
            self.models_endpoint = f"{self.endpoint}/models"

        logger.info(f"Together AI Handler Initialized: Name='{self.provider_name}', Endpoint='{self.endpoint}', DefaultModel='{self.default_model}'")

    def get_required_config_fields(self) -> List[str]:
        return ['api_key'] 

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(APIError))
    async def get_available_models(self) -> List[str]:
        # Standard OpenAI-compatible model fetching
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                # Together uses a different endpoint for listing models often (or requires specific auth)
                # Let's try the standard /models first, but be prepared for it to fail or require adjustments
                # Update: Checking Together AI docs, /models endpoint might not be standard or easily accessible
                # For now, we will return a curated list or rely on user input / default
                logger.warning("Together AI model listing via API is not reliably supported, returning common models or default.")
                # Return a list of known popular models on Together or just the default
                # Example curated list:
                known_models = [
                    "mistralai/Mixtral-8x7B-Instruct-v0.1",
                    "mistralai/Mistral-7B-Instruct-v0.2",
                    "NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO",
                    "togethercomputer/llama-2-7b-chat",
                    "togethercomputer/CodeLlama-34b-Instruct",
                    "Qwen/Qwen1.5-72B-Chat"
                ]
                if self.default_model and self.default_model not in known_models:
                     known_models.insert(0, self.default_model)
                return known_models
                
                # If standard /models endpoint was used:
                # async with session.get(self.models_endpoint, headers=headers, timeout=10) as response:
                #     if response.status != 200:
                #         # ... error handling ...
                #     data = await response.json()
                #     models = [model['id'] for model in data.get('data', [])]
                #     return models
        except Exception as e:
            logger.error(f"Error getting Together AI models (likely due to non-standard listing): {str(e)}")
            return [self.default_model] if self.default_model else []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APIError, APIResponseError)),
        reraise=True
    )
    async def _make_request(self, headers: Dict[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug(f"Sending request to Together AI endpoint: {self.chat_endpoint}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.chat_endpoint,
                    headers=headers,
                    json=payload,
                    timeout=60 # Give Together AI potentially more time
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Together AI API HTTP error: status={response.status}, response: '{error_text[:200]}...'")
                        raise APIResponseError(f"HTTP {response.status}: {error_text}")
                    return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Together AI API request failed (network error): {e}")
            raise APIError(str(e))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response from Together AI: {e}")
            raise APIResponseError(f"Invalid JSON response: {e}")

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        target_model = (model or self.default_model or "").strip()
        if not target_model:
            raise ConfigError("No model specified and no default model configured for Together AI")

        messages = [{"role": "user", "content": prompt}]
        final_api_params = self.default_api_params.copy()
        final_api_params.update(kwargs)
        
        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False, 
            **final_api_params
        }

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        try:
            result = await self._make_request(headers=headers, payload=payload)
            if "choices" in result and isinstance(result["choices"], list) and len(result["choices"]) > 0:
                first_choice = result["choices"][0]
                if "message" in first_choice and "content" in first_choice["message"]:
                    return first_choice["message"]["content"].strip()
            logger.warning(f"Together AI response format unexpected: {result}")
            raise APIResponseError("Unexpected response format from Together AI")
        except RetryError as e:
            logger.critical(f"Together AI API request failed after retries: {e}")
            raise APIError(f"API request failed after retries: {e}")

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        target_model = (model or self.default_model or "").strip()
        if not target_model:
            raise ConfigError("No model specified and no default model configured for Together AI")

        final_api_params = self.default_api_params.copy()
        final_api_params.update(kwargs)

        payload = {
            "model": target_model,
            "messages": messages,
            "stream": True,
            **final_api_params
        }

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        try:
            yield {"choices": [{"delta": {"role": "assistant"}}]}
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.chat_endpoint,
                    headers=headers,
                    json=payload,
                    timeout=60
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Together AI Stream API error: {response.status}, {error_text}")
                        yield {"error": f"API error: HTTP {response.status}"}
                        return

                    async for line in response.content:
                        if not line:
                            continue
                        line_str = line.decode('utf-8').strip()
                        if not line_str:
                            continue
                        if line_str.startswith("data: "):
                            data_str = line_str[6:].strip()
                            if data_str == "[DONE]":
                                logger.info("Together AI Stream chat completed")
                                break
                            try:
                                data = json.loads(data_str)
                                yield data 
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse Together AI stream response: {e}, data: '{data_str}'")
        except Exception as e:
            logger.error(f"Together AI stream chat error: {str(e)}")
            yield {"error": str(e)} 