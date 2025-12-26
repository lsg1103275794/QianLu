"""
Ollama Report Handler: A specialized Ollama handler for report generation tasks.
Inherits from OllamaLocalHandler to reuse common API interaction logic,
but overrides the chat method to specifically parse Ollama's non-streaming
chat responses and format them into the OpenAI-compatible structure,
including removal of <think>...</think> tags.
"""
import json
import asyncio
import re # For removing <think> tags
import time # Added for timestamp generation
from datetime import datetime, timezone # Added for ISO string parsing
from typing import Optional, Dict, Any, List

from src.utils.logging import logger
from src.providers.handlers.ollama_local import OllamaLocalHandler # Assuming this is the correct path
from src.validation.error_handler import APIResponseFormatError, APIError

class OllamaReportHandler(OllamaLocalHandler):
    """
    Specialized Ollama handler for report generation.
    Overrides the chat method for tailored response parsing.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_name = config.get('provider_name', 'ollama_report_handler') # Override provider name
        logger.info(f"Ollama Report Handler Initialized: Name='{self.provider_name}', Endpoint='{self.endpoint}', DefaultModel='{self.default_model}'")

    def _remove_think_tags(self, text: str) -> str:
        """Removes <think>...</think> tags and surrounding whitespace from text."""
        if not text:
            return ''
        # Removes the tag and any leading/trailing whitespace around the tag block itself
        # and trims overall result.
        return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL).strip()

    async def chat(self, messages: List[Any], model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Handles non-streaming chat completions with Ollama for report generation.
        Parses Ollama's specific response format and converts it to OpenAI-compatible format.
        Removes <think>...</think> tags from the content.
        """
        selected_model = model or self.default_model
        api_params = {**self.default_api_params, **kwargs} # Merge with defaults
        temperature = api_params.get('temperature')
        max_tokens = api_params.get('max_tokens')
        top_p = api_params.get('top_p')

        # 输出关键参数信息，方便调试
        logger.info(f"OllamaReportHandler使用的max_tokens值: {max_tokens}")
        logger.info(f"OllamaReportHandler使用的temperature值: {temperature}")

        payload = {
            "model": selected_model,
            "messages": self._filter_messages(messages), # Reuse parent's message filtering
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens if max_tokens is not None else -1,  # -1表示不限制
                "top_p": top_p
            }
        }
        payload["options"] = {k: v for k, v in payload["options"].items() if v is not None}
        if not payload["options"]:
            del payload["options"]

        logger.info(f"Ollama Report Handler ('{self.provider_name}') chat request to model '{selected_model}'. Payload (options only): {payload.get('options')}")
        logger.debug(f"Full Ollama Report Handler chat request payload: {json.dumps(payload, ensure_ascii=False)}")

        try:
            # Call the _make_request method from the parent class (OllamaLocalHandler)
            ollama_response = await super()._make_request("/api/chat", payload)
            
            logger.info(f"Raw response received by OllamaReportHandler from Ollama ({selected_model}):\n{json.dumps(ollama_response, indent=2, ensure_ascii=False)}")

            if not ollama_response or not isinstance(ollama_response, dict):
                raise APIResponseFormatError(
                    message="Ollama response was empty or not a dictionary.", 
                    provider_name=self.provider_name,
                    response_body=ollama_response
                )

            # Expecting Ollama's non-streaming /api/chat response format:
            # {
            #   "model": "...", "created_at": "...", 
            #   "message": {"role": "assistant", "content": "..."}, 
            #   "done": true, ...
            # }
            if 'message' in ollama_response and isinstance(ollama_response['message'], dict):
                msg_obj = ollama_response['message']
                raw_content = msg_obj.get('content', '')
                role = msg_obj.get('role', 'assistant')

                # Remove <think> tags
                cleaned_content = self._remove_think_tags(raw_content)

                # Process created_at timestamp
                created_ts = int(time.time()) # Default to current time
                created_at_str = ollama_response.get('created_at')
                if created_at_str:
                    try:
                        # Handle both 'Z' and timezone offset like +00:00
                        if created_at_str.endswith('Z'):
                            dt_object = datetime.fromisoformat(created_at_str[:-1] + '+00:00')
                        else:
                            dt_object = datetime.fromisoformat(created_at_str)
                        created_ts = int(dt_object.timestamp())
                    except ValueError:
                        logger.warning(f"Could not parse Ollama created_at: '{created_at_str}'. Using current time.")
                
                # Generate unique ID more simply
                unique_id_suffix = int(time.time() * 1000) # Milliseconds for more uniqueness

                response_data = {
                    "id": ollama_response.get('id', f"ollama-report-{selected_model}-{unique_id_suffix}"),
                    "object": "chat.completion",
                    "created": created_ts,
                    "model": ollama_response.get('model', selected_model),
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": role,
                                "content": cleaned_content, # Use cleaned content
                            },
                            "finish_reason": "stop" if ollama_response.get('done', True) else "length" # Infer finish reason
                        }
                    ],
                    "usage": { # Attempt to extract usage, defaults to 0
                        "prompt_tokens": ollama_response.get('prompt_eval_count', 0),
                        "completion_tokens": ollama_response.get('eval_count', 0),
                        "total_tokens": ollama_response.get('prompt_eval_count', 0) + ollama_response.get('eval_count', 0)
                    }
                }
                logger.info(f"Processed Ollama response into standard format by OllamaReportHandler ({selected_model}). Content length (cleaned): {len(cleaned_content)}")
                logger.debug(f"Final response_data by OllamaReportHandler:\n{json.dumps(response_data, indent=2, ensure_ascii=False)}")
                return response_data
            else:
                logger.error(f"Ollama response format unexpected by OllamaReportHandler (missing top-level 'message' object or it's not a dict): {json.dumps(ollama_response, indent=2, ensure_ascii=False)}")
                raise APIResponseFormatError(
                    message="Ollama response format did not contain the expected 'message' object.",
                    provider_name=self.provider_name,
                    response_body=ollama_response
                )

        except APIError as e: # Catch APIError and its children from _make_request or self
            logger.error(f"APIError during OllamaReportHandler chat for model '{selected_model}': {e.message}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in OllamaReportHandler chat (model: {selected_model}): {e}")
            # Wrap unexpected errors in our generic APIError
            raise APIError(message=f"Ollama Report Handler chat failed: {e}", provider_name=self.provider_name, details=str(e))

# Example usage (for testing, not part of the class):
# async def main():
#     config = {"endpoint": "http://localhost:11434", "default_model": "llama3"}
#     handler = OllamaReportHandler(config)
#     messages = [{"role": "user", "content": "Tell me a joke about AI and reports. <think>I should make it short and witty.</think>"}]
#     try:
#         response = await handler.chat(messages=messages, model="qwen:0.5b") # Use a small model for quick test
#         print("\nFormatted Response:")
#         print(json.dumps(response, indent=2, ensure_ascii=False))
#     except Exception as e:
#         print(f"An error occurred: {e}")

# if __name__ == '__main__':
#      asyncio.run(main()) 