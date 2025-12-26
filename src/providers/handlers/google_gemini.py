"""
Google Gemini API handler implementation.
"""
import json
import aiohttp
import os
# --- Add asyncio --- 
import asyncio 
# -------------------
from typing import Optional, Dict, Any, List, AsyncGenerator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
import google.generativeai as genai
from google.generativeai.types import content_types
from google.generativeai.types.generation_types import GenerateContentResponse, GenerationConfig
# --- FIX: Import specific Google API errors --- 
from google.api_core import exceptions as google_exceptions
# --------------------------------------------

from src.utils.logging import logger
from src.providers.base import BaseAPIHandler
# --- Use correct exception names from error_handler.py --- 
from src.validation.error_handler import ConfigurationError as ConfigError, APIError, APIResponseError, APIResponseFormatError, APIConnectionError, APITimeoutError # Use updated names
# ---------------------------------------------------------
from src.utils.retry import is_retryable_exception

class GoogleGeminiHandler(BaseAPIHandler):
    """Handles interaction with Google Gemini API."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_name = config.get('provider_name', 'google_gemini')
        env_prefix = "GOOGLE_" # Define prefix
        
        # --- 修改：读取带前缀的扁平化配置 --- 
        # credentials = config.get('credentials', {})
        # self.api_key = credentials.get('api_key')
        self.api_key = config.get(f'{env_prefix}API_KEY')
        
        # Endpoint might not be directly used by SDK, but keep for potential future use/consistency
        self.endpoint = config.get(f'{env_prefix}ENDPOINT') 
        self.default_model = config.get(f'{env_prefix}DEFAULT_MODEL')
        self.project_id = config.get(f'{env_prefix}PROJECT_ID') # Keep project_id if relevant for some SDK features
        
        # --- 修改：读取带前缀的参数 --- 
        self.default_api_params = {
            'temperature': config.get(f'{env_prefix}TEMPERATURE', 0.7),
            'top_p': config.get(f'{env_prefix}TOP_P', 1.0),
            'top_k': config.get(f'{env_prefix}TOP_K', 40),
            'max_tokens': config.get(f'{env_prefix}MAX_TOKENS', 2048) # Maps to max_output_tokens
        }
        
        # self.request_timeout = config.get('request_timeout', 120)
        # Timeout might be handled differently by SDK, but read for consistency
        self.request_timeout = config.get(f'{env_prefix}REQUEST_TIMEOUT', 120) 

        if not self.api_key:
            # --- 修改：更新错误信息 --- 
            raise ConfigError(f"Provider '{self.provider_name}' is missing required '{env_prefix}API_KEY'.")
            # -------------------------

        try:
            genai.configure(api_key=self.api_key)
            logger.info(f"Google Gemini SDK configured successfully for provider '{self.provider_name}'.")
        except Exception as e:
             logger.error(f"Failed to configure Google Gemini SDK for '{self.provider_name}': {e}", exc_info=True)
             # --- Use ConfigError --- 
             raise ConfigError(f"Failed to configure Google Gemini SDK for '{self.provider_name}' with provided API Key: {e}")
             # -------------------------
        
        logger.info(f"Google Gemini Handler Initialized: Name='{self.provider_name}', DefaultModel='{self.default_model}', ProjectID='{self.project_id}'")

    def get_required_config_fields(self) -> List[str]:
        """Get the list of required configuration fields (prefixed env vars)."""
        # --- 修改：返回带前缀的环境变量名 --- 
        # return ['credentials']
        env_prefix = "GOOGLE_"
        return [f'{env_prefix}API_KEY'] 
        # ----------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        # --- Use updated retry logic/exceptions --- 
        retry=is_retryable_exception, # Check if this covers google_exceptions.GoogleAPIError subtypes
        # retry=retry_if_exception_type((google_exceptions.GoogleAPIError, APIError)), # Be explicit if needed
        # -----------------------------------------
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
             f"Gemini models fetch failed (attempt {retry_state.attempt_number}), retrying. Reason: {retry_state.outcome.exception()}"
         )
    )
    async def get_available_models(self) -> List[str]:
        """Get available models using the Google Gemini SDK."""
        logger.info(f"Attempting to fetch Google Gemini models using SDK for '{self.provider_name}'...")
        try:
            # --- Use asyncio.to_thread for SDK calls --- 
            # available_model_names = []
            # for model_info in genai.list_models():
            #      if 'generateContent' in model_info.supported_generation_methods:
            #           model_id = model_info.name.split('models/', 1)[-1]
            #           available_model_names.append(model_id)
            def list_sync_models():
                models = []
                for model_info in genai.list_models():
                    if 'generateContent' in model_info.supported_generation_methods:
                        model_id = model_info.name.split('models/', 1)[-1]
                        models.append(model_id)
                return models
            
            available_model_names = await asyncio.to_thread(list_sync_models)
            # ---------------------------------------------
                      
            logger.info(f"Available Google Gemini generative models for '{self.provider_name}': {available_model_names}")
            return available_model_names
        except google_exceptions.PermissionDenied as e:
            logger.error(f"Google API permission denied fetching models for '{self.provider_name}': {str(e)}. Check API Key and permissions.")
            raise APIError(message="API Permission Denied", detail=str(e), provider=self.provider_name) from e
        except google_exceptions.Unauthenticated as e:
            logger.error(f"Google API authentication failed fetching models for '{self.provider_name}': {str(e)}. Check API Key.")
            raise ConfigError(message="API Authentication Failed", detail=str(e), provider=self.provider_name) from e # Treat as config error
        except google_exceptions.GoogleAPIError as e:
            logger.error(f"Google API error getting models for '{self.provider_name}': {str(e)}", exc_info=True)
            # --- Use specific errors if possible --- 
            if isinstance(e, google_exceptions.ServiceUnavailable):
                 raise APIConnectionError(message="Google API Service Unavailable", detail=str(e), provider=self.provider_name) from e
            elif isinstance(e, google_exceptions.ResourceExhausted):
                 raise APIResponseError(message="Google API Resource Exhausted (Quota?)", status_code=429, response_body={"error": str(e)}, provider=self.provider_name) from e
            else:
                 raise APIError(message=f"Google API error fetching models: {str(e)}", detail=str(e), provider=self.provider_name) from e
            # ---------------------------------------
        except Exception as e:
            logger.error(f"Generic error getting Google Gemini models for '{self.provider_name}': {str(e)}", exc_info=True)
            # --- Use APIError --- 
            raise APIError(message=f"Failed to fetch models: {str(e)}", detail=str(e), provider=self.provider_name) from e
            # -------------------------

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate text using the API."""
        # Adapt simple prompt to message format for consistency 
        messages = [{"role": "user", "content": prompt}]
        # --- Use stream_chat internally and collect result --- 
        # return await self.generate_text(prompt, model, **kwargs)
        full_response = ""
        try:
             async for chunk in self.stream_chat(messages=messages, model=model, **kwargs):
                 if "choices" in chunk and chunk["choices"]:
                      delta = chunk["choices"][0].get("delta", {})
                      content = delta.get("content")
                      if content:
                           full_response += content
                 elif "error" in chunk:
                      logger.error(f"Error received during generate (via stream_chat) for '{self.provider_name}': {chunk['error']}")
                      # Re-raise a standard error for generate?
                      detail = chunk.get('detail', chunk['error'])
                      raise APIResponseError(message=f"Error generating text: {detail}", response_body=chunk, provider=self.provider_name)
                 elif chunk.get("status") == "done":
                      break # Stream finished
             return full_response.strip()
        except APIError as e:
             # Logged in stream_chat, re-raise
             raise e
        except Exception as e:
             logger.exception(f"Unexpected error in generate (via stream_chat) for '{self.provider_name}': {e}")
             raise APIError(message=f"Unexpected error generating text: {e}", provider=self.provider_name) from e
        # --------------------------------------------------

    def _convert_to_gemini_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert OpenAI format messages to Gemini format. Handles system prompt merging."""
        gemini_messages = []
        current_user_content = []
        system_prompt = None

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                system_prompt = content 
            elif role == "user":
                current_user_content.append(content)
            elif role == "assistant":
                if current_user_content:
                    full_user_content = "\n".join(current_user_content)
                    if system_prompt and not any(m['role'] == 'user' for m in gemini_messages):
                        full_user_content = f"{system_prompt}\n\n{full_user_content}"
                        system_prompt = None 
                    gemini_messages.append({"role": "user", "content": full_user_content})
                    current_user_content = []
                gemini_messages.append({"role": "model", "content": content}) 
            else:
                logger.warning(f"Unsupported message role '{role}' for Gemini in provider '{self.provider_name}', skipping")

        if current_user_content:
            full_user_content = "\n".join(current_user_content)
            if system_prompt and not any(m['role'] == 'user' for m in gemini_messages):
                full_user_content = f"{system_prompt}\n\n{full_user_content}"
            gemini_messages.append({"role": "user", "content": full_user_content})

        if gemini_messages and gemini_messages[0]['role'] != 'user' and system_prompt:
             gemini_messages.insert(0, {"role": "user", "content": system_prompt})
        elif not gemini_messages and system_prompt:
             gemini_messages.append({"role": "user", "content": system_prompt})
             
        last_role = None
        for i, msg in enumerate(gemini_messages):
            if msg['role'] == last_role:
                logger.warning(f"Gemini message sequence for '{self.provider_name}' has non-alternating roles at index {i}. SDK might raise error.")
            last_role = msg['role']
            
        return gemini_messages

    def _create_generation_config(self, params: Dict[str, Any]) -> GenerationConfig:
        """Create Gemini generation config from parameters, filtering None values."""
        config_params = {
            "temperature": params.get("temperature"),
            "top_p": params.get("top_p"),
            "top_k": params.get("top_k"),
            "max_output_tokens": params.get("max_tokens"),
            "stop_sequences": [params["stop"]] if isinstance(params.get("stop"), str) else params.get("stop")
        }
        filtered_config = {k: v for k, v in config_params.items() if v is not None}
        if "stop_sequences" in filtered_config and not isinstance(filtered_config["stop_sequences"], list):
            logger.warning(f"Gemini stop sequences for '{self.provider_name}' should be a list, got {type(filtered_config['stop_sequences'])}. Attempting to wrap.")
            filtered_config["stop_sequences"] = [str(filtered_config["stop_sequences"])]
            
        return GenerationConfig(**filtered_config)

    # --- stream_chat --- 
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        # --- Retry on retryable Google API errors --- 
        retry=retry_if_exception_type((google_exceptions.ServiceUnavailable, google_exceptions.ResourceExhausted)),
        # ---------------------------------------------
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
             f"Gemini stream_chat call failed (attempt {retry_state.attempt_number}), retrying. Reason: {retry_state.outcome.exception()}"
         )
    )
    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate response using Google Gemini API (streaming chat)."""
        target_model = model or self.default_model
        if not target_model:
            raise ConfigError(f"Provider '{self.provider_name}' has no model specified and no default model configured")

        env_prefix = "GOOGLE_"
        # --- 修改：使用 get_current_param 读取最新参数 --- 
        temperature = self.get_current_param("temperature", "float", self.default_api_params.get('temperature'))
        max_tokens = self.get_current_param("max_tokens", "int", self.default_api_params.get('max_tokens'))
        top_p = self.get_current_param("top_p", "float", self.default_api_params.get('top_p'))
        top_k = self.get_current_param("top_k", "int", self.default_api_params.get('top_k'))
        stop = self.get_current_param("stop", "str_or_list", None) # Handle string or list
        
        final_api_params = {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "top_k": top_k,
            "stop": stop
        }
        # Merge remaining kwargs, respecting those already set
        final_api_params.update({k: v for k, v in kwargs.items() if k not in final_api_params})
        # -------------------------------------------------
        
        generation_config = self._create_generation_config(final_api_params)
        gemini_messages = self._convert_to_gemini_messages(messages)

        if not gemini_messages or gemini_messages[0]['role'] != 'user':
             # Gemini SDK requires the first message to be from the user
             logger.error(f"Gemini message list must start with a user role for '{self.provider_name}'. Messages: {gemini_messages}")
             yield {"error": "Invalid message sequence: Must start with user role.", "provider": self.provider_name}
             return

        try:
            # --- Ensure model name includes 'models/' prefix --- 
            if not target_model.startswith('models/'):
                 sdk_model_name = f'models/{target_model}'
            else:
                 sdk_model_name = target_model
            # ---------------------------------------------------
                 
            model_instance = genai.GenerativeModel(sdk_model_name)
            
            logger.info(f"Calling Google Gemini API (stream_chat): Model='{sdk_model_name}' for '{self.provider_name}'")
            logger.debug(f"Google Gemini API stream_chat effective params for '{self.provider_name}': {generation_config}")
            logger.debug(f"Google Gemini API stream_chat messages for '{self.provider_name}': {gemini_messages}")

            # --- Use asyncio.to_thread for blocking SDK stream call --- 
            # response_stream = await model_instance.generate_content_async(
            #     gemini_messages,
            #     generation_config=generation_config,
            #     stream=True
            # )
            def generate_sync_stream():
                # This will block the thread until the stream is consumed
                return model_instance.generate_content(
                    gemini_messages,
                    generation_config=generation_config,
                    stream=True
                )
            
            response_stream = await asyncio.to_thread(generate_sync_stream)
            # ---------------------------------------------------------

            # Yield assistant role start? OpenAI format expects this.
            yield {"choices": [{"index": 0, "delta": {"role": "assistant"}}]}

            # --- Process stream --- 
            async for chunk in response_stream:
                try:
                    # Check for blocked content
                    if not chunk.parts:
                         if chunk.prompt_feedback and chunk.prompt_feedback.block_reason:
                              block_reason = chunk.prompt_feedback.block_reason.name
                              logger.warning(f"Gemini stream chunk blocked for '{self.provider_name}'. Reason: {block_reason}")
                              yield {"error": f"Content blocked by API during streaming. Reason: {block_reason}", "provider": self.provider_name}
                              # Should we stop here or continue?
                              break # Stop yielding on block
                         else:
                              # Empty parts but no block reason? Log and skip
                              logger.warning(f"Gemini stream chunk has no parts and no block reason for '{self.provider_name}'. Chunk: {chunk}")
                              continue 
                              
                    chunk_text = chunk.text
                    if chunk_text:
                        yield {
                             "choices": [
                                 {
                                     "index": 0,
                                     "delta": {"content": chunk_text},
                                     "finish_reason": None # Gemini stream doesn't typically provide this per chunk
                                 }
                             ]
                         }
                except ValueError as e:
                     # Handle cases where chunk.text raises ValueError (e.g., safety settings)
                     logger.error(f"Gemini stream chunk text access error (likely blocked) for '{self.provider_name}': {e}")
                     block_reason = "SafetySettings/Unknown"
                     if chunk.prompt_feedback and chunk.prompt_feedback.block_reason:
                         block_reason = chunk.prompt_feedback.block_reason.name
                     yield {"error": f"Content blocked by API during streaming (ValueError). Reason: {block_reason}", "provider": self.provider_name}
                     break # Stop yielding on block
                except Exception as e:
                     logger.exception(f"Error processing Gemini stream chunk for '{self.provider_name}': {e}")
                     # Don't yield raw exception, maybe a generic error message
                     yield {"error": f"Internal error processing stream chunk: {str(e)[:100]}...", "provider": self.provider_name}
                     # Continue or break? Let's break to be safe.
                     break
            # ---------------------
                     
            # Indicate stream completion - OpenAI format
            yield {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]} # Assume stop
            yield {"status": "done"}
            logger.info(f"Google Gemini stream chat completed for '{self.provider_name}'.")

        # --- Map specific Google API errors --- 
        except google_exceptions.InvalidArgument as e:
             logger.error(f"Google API Invalid Argument error during stream_chat for '{self.provider_name}': {str(e)}. Check messages/params.", exc_info=True)
             yield {"error": f"Invalid Argument: {str(e)}", "detail": str(e), "provider": self.provider_name}
        except google_exceptions.PermissionDenied as e:
            logger.error(f"Google API permission denied during stream_chat for '{self.provider_name}': {str(e)}. Check API Key.")
            yield {"error": "API Permission Denied", "detail": str(e), "provider": self.provider_name}
        except google_exceptions.Unauthenticated as e:
            logger.error(f"Google API authentication failed during stream_chat for '{self.provider_name}': {str(e)}. Check API Key.")
            yield {"error": "API Authentication Failed", "detail": str(e), "provider": self.provider_name}
        except google_exceptions.ResourceExhausted as e: 
             logger.error(f"Google API Resource Exhausted during stream_chat for '{self.provider_name}': {str(e)}. (Quota?)")
             yield {"error": "API Resource Exhausted (Quota?) (Code: 429)", "detail": str(e), "status_code": 429, "provider": self.provider_name}
        except google_exceptions.ServiceUnavailable as e:
             logger.error(f"Google API Service Unavailable during stream_chat for '{self.provider_name}': {str(e)}")
             yield {"error": "API Service Unavailable", "detail": str(e), "provider": self.provider_name}
        except google_exceptions.GoogleAPIError as e:
             logger.error(f"Google API error during stream_chat for '{self.provider_name}': {str(e)}", exc_info=True)
             yield {"error": f"Google API Error: {str(e)}", "detail": str(e), "provider": self.provider_name}
        # ---------------------------------------
        except RetryError as e:
             logger.critical(f"Google Gemini SDK call failed after retries for '{self.provider_name}' (stream_chat): {e}")
             yield {"error": f"API request failed after retries: {str(e.last_attempt.exception())[:100]}...", "detail": str(e.last_attempt.exception()), "provider": self.provider_name}
        except Exception as e:
            logger.exception(f"Unexpected error during Google Gemini stream_chat for '{self.provider_name}': {e}")
            yield {"error": f"Unexpected internal error during streaming: {str(e)[:100]}...", "provider": self.provider_name}
        finally:
             logger.info(f"Gemini stream processing ended for {self.provider_name}.")

    # --- analyze_image --- 
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        # --- Retry on specific Google errors --- 
        retry=retry_if_exception_type((google_exceptions.ServiceUnavailable, google_exceptions.ResourceExhausted)),
        # ---------------------------------------
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
             f"Gemini analyze_image call failed (attempt {retry_state.attempt_number}), retrying. Reason: {retry_state.outcome.exception()}"
         )
    )
    async def analyze_image(
        self,
        image_data: bytes, # Expecting bytes for image data
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """Analyze an image using Google Gemini vision model."""
        target_model = model or self.default_model
        if not target_model:
            raise ConfigError(f"Provider '{self.provider_name}' has no model specified for image analysis")
            
        # --- Ensure model is vision capable (simple check) --- 
        if "vision" not in target_model and "gemini-1.5-pro" not in target_model and "gemini-pro-vision" not in target_model:
             logger.warning(f"Model '{target_model}' selected for image analysis in '{self.provider_name}' does not seem to be a vision model. Trying anyway.")
        # -----------------------------------------------------
        
        env_prefix = "GOOGLE_"
        # --- 修改：使用 get_current_param 读取最新参数 --- 
        # Reuse text generation params where applicable
        temperature = self.get_current_param("temperature", "float", self.default_api_params.get('temperature'))
        max_tokens = self.get_current_param("max_tokens", "int", self.default_api_params.get('max_tokens'))
        top_p = self.get_current_param("top_p", "float", self.default_api_params.get('top_p'))
        top_k = self.get_current_param("top_k", "int", self.default_api_params.get('top_k'))
        stop = self.get_current_param("stop", "str_or_list", None)
        
        final_api_params = {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "top_k": top_k,
            "stop": stop
        }
        final_api_params.update({k: v for k, v in kwargs.items() if k not in final_api_params})
        # -------------------------------------------------
        
        generation_config = self._create_generation_config(final_api_params)
        
        try:
            # --- Prepare image content for SDK --- 
            # Assuming image_data is bytes. Need to determine mime type if not provided.
            # Basic image type detection (can be improved)
            mime_type = "image/jpeg" # Default
            if image_data.startswith(b'\x89PNG\r\n\x1a\n'):
                mime_type = "image/png"
            elif image_data.startswith(b'\xff\xd8\xff'):
                 mime_type = "image/jpeg"
            elif image_data.startswith(b'GIF87a') or image_data.startswith(b'GIF89a'):
                 mime_type = "image/gif"
            elif image_data.startswith(b'RIFF') and image_data[8:12] == b'WEBP':
                 mime_type = "image/webp"
                 
            logger.info(f"Detected image mime-type as {mime_type} for '{self.provider_name}'")
            image_part = {"mime_type": mime_type, "data": image_data}
            # -------------------------------------

            # --- Ensure model name includes 'models/' prefix --- 
            if not target_model.startswith('models/'):
                 sdk_model_name = f'models/{target_model}'
            else:
                 sdk_model_name = target_model
            # ---------------------------------------------------
            model_instance = genai.GenerativeModel(sdk_model_name)

            logger.info(f"Calling Google Gemini API (analyze_image): Model='{sdk_model_name}' for '{self.provider_name}'")
            logger.debug(f"Google Gemini API analyze_image effective params for '{self.provider_name}': {generation_config}")

            # --- Use asyncio.to_thread for blocking SDK call --- 
            # response = await model_instance.generate_content_async(
            #     [prompt, image_part],
            #     generation_config=generation_config
            # )
            def analyze_sync():
                return model_instance.generate_content(
                    [prompt, image_part], 
                    generation_config=generation_config
                )
            
            response = await asyncio.to_thread(analyze_sync)
            # -------------------------------------------------

            # --- Check response for content and potential blocks --- 
            try:
                generated_text = response.text
            except ValueError as e:
                 logger.error(f"Gemini image analysis response blocked or invalid for '{self.provider_name}'. Prompt: '{prompt[:100]}...'. Error: {e}")
                 block_reason = "Unknown"
                 if response.prompt_feedback and response.prompt_feedback.block_reason:
                      block_reason = response.prompt_feedback.block_reason.name
                 raise APIResponseError(message=f"Content blocked by API. Reason: {block_reason}", response_body={"error": str(e), "block_reason": block_reason}, provider=self.provider_name) from e
            # ---------------------------------------------------------
                 
            if not generated_text:
                 logger.warning(f"Empty response text from Gemini image analysis for '{self.provider_name}'. Prompt: '{prompt[:100]}...'")
                 return ""
            
            return generated_text.strip()

        # --- Map specific Google API errors --- 
        except google_exceptions.InvalidArgument as e:
             logger.error(f"Google API Invalid Argument error during analyze_image for '{self.provider_name}': {str(e)}. Check prompt/image/params.", exc_info=True)
             raise APIError(message=f"Invalid Argument: {str(e)}", detail=str(e), provider=self.provider_name) from e
        except google_exceptions.PermissionDenied as e:
            logger.error(f"Google API permission denied during analyze_image for '{self.provider_name}': {str(e)}. Check API Key.")
            raise APIError(message="API Permission Denied", detail=str(e), provider=self.provider_name) from e
        except google_exceptions.Unauthenticated as e:
            logger.error(f"Google API authentication failed during analyze_image for '{self.provider_name}': {str(e)}. Check API Key.")
            raise ConfigError(message="API Authentication Failed", detail=str(e), provider=self.provider_name) from e
        except google_exceptions.ResourceExhausted as e: 
             logger.error(f"Google API Resource Exhausted during analyze_image for '{self.provider_name}': {str(e)}. (Quota?)")
             raise APIResponseError(message="API Resource Exhausted (Quota?)", status_code=429, response_body={"error": str(e)}, provider=self.provider_name) from e
        except google_exceptions.ServiceUnavailable as e:
             logger.error(f"Google API Service Unavailable during analyze_image for '{self.provider_name}': {str(e)}")
             raise APIConnectionError(message="Google API Service Unavailable", detail=str(e), provider=self.provider_name) from e
        except google_exceptions.GoogleAPIError as e:
             logger.error(f"Google API error during analyze_image for '{self.provider_name}': {str(e)}", exc_info=True)
             raise APIError(message=f"Google API Error: {str(e)}", detail=str(e), provider=self.provider_name) from e
        # ---------------------------------------
        except RetryError as e:
             logger.critical(f"Google Gemini SDK call failed after retries for '{self.provider_name}' (analyze_image): {e}")
             raise APIError(f"API request failed after retries: {str(e.last_attempt.exception())[:100]}...", detail=str(e.last_attempt.exception()), provider=self.provider_name) from e
        except Exception as e:
            logger.exception(f"Unexpected error during Google Gemini analyze_image for '{self.provider_name}': {e}")
            raise APIError(message=f"Unexpected internal error during image analysis: {str(e)[:100]}...", provider=self.provider_name) from e