"""
Groq API handler implementation (OpenAI Compatible).
"""
import json
import aiohttp
from typing import Optional, Dict, Any, List, AsyncGenerator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError

from src.utils.logging import logger
from src.providers.base import BaseAPIHandler
from src.utils.error_handler import ConfigError, APIError, APIResponseError
from src.utils.retry import is_retryable_exception

class GroqApiHandler(BaseAPIHandler):
    """Handles interaction with Groq API (OpenAI Compatible)."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Configuration specific to Groq, defaults if not provided
        self.provider_name = config.get('provider_name', 'groq_api')
        self.api_key = config.get('api_key')
        self.endpoint = config.get('endpoint', 'https://api.groq.com/openai/v1') # Default Groq endpoint
        self.default_model = config.get('default_model', 'llama3-8b-8192') # Groq often has specific models
        self.default_api_params = {
            'temperature': config.get('temperature', 0.7),
            'top_p': config.get('top_p', 1.0),
            'max_tokens': config.get('max_tokens', 2048) # Default max tokens
        }

        if not self.api_key:
            raise ConfigError(f"Provider '{self.provider_name}' is missing required 'api_key' configuration.")
        if not self.endpoint:
            # This should ideally not happen if default is set, but good practice
            raise ConfigError(f"Provider '{self.provider_name}' is missing required 'endpoint' configuration.")

        # Ensure chat_endpoint is set correctly
        if self.endpoint.endswith('/'):
            self.chat_endpoint = f"{self.endpoint}chat/completions"
            self.models_endpoint = f"{self.endpoint}models" # Added for consistency
        else:
            self.chat_endpoint = f"{self.endpoint}/chat/completions"
            self.models_endpoint = f"{self.endpoint}/models" # Added for consistency

        logger.info(f"Groq API Handler Initialized: Name='{self.provider_name}', Endpoint='{self.endpoint}', DefaultModel='{self.default_model}'")

    def get_required_config_fields(self) -> List[str]:
        """Get the list of required configuration fields."""
        return ['api_key'] # Endpoint has a default

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(APIError),
        reraise=True
    )
    async def get_available_models(self) -> List[str]:
        """Get available models from the Groq API."""
        # Standard OpenAI-compatible model fetching
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.models_endpoint, 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Groq API error fetching models: {response.status}, {error_text}")
                        raise APIError(f"Failed to fetch models: HTTP {response.status}")
                    
                    data = await response.json()
                    models = [model['id'] for model in data.get('data', []) if isinstance(model, dict) and 'id' in model]
                    logger.info(f"Available Groq models: {models}")
                    return models
        except aiohttp.ClientError as e:
            logger.error(f"Groq API connection error fetching models: {e}")
            raise APIError(f"Connection error: {e}")
        except Exception as e:
            logger.error(f"Error getting Groq models: {str(e)}")
            # Fallback to default model if fetching fails
            return [self.default_model] if self.default_model else []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APIError, APIResponseError)),
        reraise=True
    )
    async def _make_request(self, headers: Dict[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make an HTTP POST request to the API with retry logic."""
        logger.debug(f"Sending request to Groq endpoint: {self.chat_endpoint}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.chat_endpoint,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60) # Increased timeout for potentially longer Groq requests
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Groq API HTTP error: status={response.status}, response: '{error_text[:200]}...'")
                        raise APIResponseError(f"HTTP {response.status}: {error_text}")

                    return await response.json()

        except aiohttp.ClientError as e:
            logger.error(f"Groq API request failed (network error): {e}")
            raise APIError(str(e))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response from Groq: {e}")
            raise APIResponseError(f"Invalid JSON response: {e}")

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate text using the Groq API."""
        target_model = (model or self.default_model or "").strip()
        if not target_model:
            raise ConfigError("No model specified and no default model configured for Groq")

        # Prepare request payload
        messages = [{"role": "user", "content": prompt}]
        final_api_params = self.default_api_params.copy()
        final_api_params.update(kwargs) # Apply overrides
        
        # Ensure stream is False for generate
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

            logger.warning(f"Groq response format unexpected: {result}")
            raise APIResponseError("Unexpected response format from Groq")

        except RetryError as e:
            logger.critical(f"Groq API request failed after retries: {e}")
            raise APIError(f"API request failed after retries: {e}")

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat responses from the Groq API."""
        target_model = (model or self.default_model or "").strip()
        if not target_model:
            raise ConfigError("No model specified and no default model configured for Groq")

        # Prepare request payload
        final_api_params = self.default_api_params.copy()
        final_api_params.update(kwargs) # Apply overrides

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
            # First yield the assistant role for compatibility
            yield {"choices": [{"delta": {"role": "assistant"}}]}

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.chat_endpoint,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60) # Increased timeout for stream
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Groq Stream API error: {response.status}, {error_text}")
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
                                logger.info("Groq Stream chat completed")
                                break
                            try:
                                data = json.loads(data_str)
                                yield data # Yield the parsed JSON chunk directly
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse Groq stream response: {e}, data: '{data_str}'")
                                # Optionally yield raw content on error, but might break frontend
                                # yield {"choices": [{"delta": {"content": data_str}}]}

        except Exception as e:
            logger.error(f"Groq stream chat error: {str(e)}")
            yield {"error": str(e)} 