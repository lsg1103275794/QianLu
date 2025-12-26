"""
Core logic for style transfer: imitating the style of a source text 
to generate new content on a different theme.
"""
from typing import Dict, Any, Optional
from src.utils.logging import logger
from src.providers.factory import get_handler
from src.config.api_manager import api_manager
import json # Import json for potential future use with guidance

class StyleTransfer:

    async def transfer_style(
        self,
        new_content_prompt: str,
        api_provider: str,
        model: str,
        style_guidance: str, # Made non-optional as it's always provided now
        style_source_text: Optional[str] = None # Keep for signature, but ignore
    ) -> str:
        """Generate new text based on new_content_prompt, following the provided style_guidance."""
        logger.info(f"Starting style transfer (Stage 2): Provider='{api_provider}', Model='{model}'")
        
        # Validation (optional, as upstream should ensure guidance exists)
        if not style_guidance:
            raise ValueError("Style guidance is required for transfer_style.")

        try:
            if not api_manager.is_provider_configured(api_provider):
                raise ValueError(f"API provider '{api_provider}' is not configured")

            handler = get_handler(api_provider)

            # Model availability check (can keep as is)
            try:
                available_models = await handler.get_available_models()
                if model not in available_models:
                    logger.warning(f"Model '{model}' not found in available list for provider '{api_provider}'. Attempting to use anyway.")
            except Exception as model_err:
                logger.warning(f"Could not verify model availability for {api_provider}: {model_err}. Proceeding anyway.")

            # --- Construct the prompt using ONLY style guidance --- 
            logger.debug("Constructing prompt using style guidance for generation.")
            prompt = f"""
请严格根据以下【写作风格指南】中描述的风格特点，创作一段关于【新内容主题】的文本。

【写作风格指南】:
{style_guidance}

【新内容主题】:
{new_content_prompt}

重要要求：
1.  **遵循指南**: 输出的文本必须严格遵循【写作风格指南】中描述的风格。
2.  **内容相关**: 输出的文本必须紧密围绕【新内容主题】展开。
3.  **输出纯粹**: 请直接输出新创作的文本内容，不要包含任何解释、引言、总结或与新创作内容无关的文字。
"""
            # --- End of prompt construction ---

            logger.debug(f"Generated Style Transfer Prompt (Stage 2 - first 300 chars):\n{prompt[:300]}...")

            # --- LLM Call (remains the same) ---
            response_content = None
            if hasattr(handler, 'generate_text'):
                 response_content = await handler.generate_text(
                    prompt=prompt,
                    model=model
                 )
            elif hasattr(handler, 'chat'):
                 messages = [
                     {"role": "system", "content": "You are a helpful assistant that generates text following specific style instructions."},
                     {"role": "user", "content": prompt}
                 ]
                 chat_response = await handler.chat(
                     messages=messages,
                     model=model
                 )
                 if isinstance(chat_response, dict) and 'content' in chat_response:
                     response_content = chat_response['content']
                 elif isinstance(chat_response, object) and hasattr(chat_response, 'content'):
                     response_content = chat_response.content
                 elif isinstance(chat_response, str):
                      response_content = chat_response
                 else:
                      logger.warning(f"Unexpected chat response format from handler: {type(chat_response)}")
                      response_content = str(chat_response)
            else:
                 raise NotImplementedError(f"Handler for provider '{api_provider}' does not support required 'generate_text' or 'chat' methods.")

            if response_content is None:
                logger.error("LLM handler did not return usable content.")
                raise ValueError("Failed to generate content from the AI provider.")

            logger.info("Style transfer generation (Stage 2) successful.")
            # Basic cleaning: remove potential markdown fences or leading/trailing whitespace from final output
            cleaned_output = response_content.strip().removeprefix('```').removesuffix('```').strip()
            return cleaned_output if isinstance(cleaned_output, str) else str(cleaned_output) 

        except Exception as e:
            logger.exception(f"Error during style transfer processing (Stage 2): {e}")
            raise 