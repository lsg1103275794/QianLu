"""
API route for style transfer.
"""

from fastapi import APIRouter, HTTPException, Body, status, Depends
from pydantic import BaseModel, Field
from typing import Optional, Any

# --- Database Imports ---
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.manager import get_db
# -----------------------

from src.core.processing.style_transfer import StyleTransfer
from src.utils.logging import logger
from src.utils.error_handler import handle_error, raise_http_error
from src.utils.cache import get_analysis_result
from src.providers.factory import get_handler # Import the handler factory
import json
import re # Import re for potential splitting

# --- Configuration ---
# Threshold for splitting the new_theme prompt into segments (adjust as needed)
SEGMENT_THRESHOLD_CHARS = 1500 
# Simple paragraph splitter (could be more sophisticated)
def split_into_paragraphs(text):
    # Split by double newlines, keeping non-empty paragraphs
    paragraphs = [p.strip() for p in text.split('\\n\\n') if p.strip()]
    # Further split very long paragraphs if necessary (optional enhancement)
    # ... 
    return paragraphs if paragraphs else [text] # Return list even if no split

# --- Pydantic Models ---

class TransferRequest(BaseModel):
    input_type: str = Field(..., description="Input type: 'text', 'file', or 'analysis'")
    source_text: Optional[str] = Field(None, description="Source text (used if input_type is 'text' or 'file')")
    analysis_report_id: Optional[str] = Field(None, description="ID of the analysis report (used if input_type is 'analysis')")
    file_path: Optional[str] = Field(None, description="Path to the uploaded file (used if input_type is 'file')") # Keep for potential future use
    new_theme: str = Field(..., description="The new theme or topic to write about in the target style")
    provider: str = Field(..., description="API provider name")
    model: str = Field(..., description="Model name")
    # Add other potential parameters like target_style if needed later

class TransferResponse(BaseModel):
    status: str = Field("success", description="Indicates success")
    result: str = Field(..., description="The generated text in the target style")

# --- Router Definition ---
router = APIRouter(
    prefix="/transfer", 
    tags=["Style Transfer"]
)

# --- Style Transfer Instance ---
# Create a single instance (if stateless) or manage as needed
style_transfer_processor = StyleTransfer()

# --- Helper function for Stage 1: Extracting Style Guidance ---
async def _extract_style_guidance(text: str, provider: str, model: str) -> str:
    """Calls the LLM to extract style guidance from the given text."""
    logger.info(f"Extracting style guidance using {provider}/{model}...")
    guidance_prompt = f"""
请仔细分析以下【文本原文】的写作风格、语气、常用句式、词汇特点、段落结构和整体氛围。
不要进行任何模仿或创作，专注于分析。
请将分析结果总结为一份清晰、简洁、结构化的【写作风格指南】，以便后续模型可以依据此指南进行模仿创作。

【文本原文】:
```
{text}
```

【输出要求】:
1.  **专注分析**: 你的输出应该只包含【写作风格指南】本身。
2.  **结构清晰**: 指南内容应分点或分段，清晰描述不同方面的风格特征。
3.  **简洁准确**: 抓住核心风格特点，避免冗余描述。
4.  **禁止创作**: 不要包含任何基于原文的二次创作或对新主题的联想。
5.  **纯粹输出**: 不要添加任何解释、引言、开头语（例如"好的，这是分析结果："）或结束语。

请直接输出【写作风格指南】：
"""
    try:
        handler = get_handler(provider) # Reuse get_handler logic
        # Check model availability (optional but recommended)
        try:
            available_models = await handler.get_available_models()
            if model not in available_models:
                 logger.warning(f"Model '{model}' not in available list for guidance extraction, using anyway.")
        except Exception as model_err:
             logger.warning(f"Could not verify model for guidance extraction: {model_err}")
             
        extracted_guidance = None
        if hasattr(handler, 'generate_text'):
            extracted_guidance = await handler.generate_text(prompt=guidance_prompt, model=model)
        elif hasattr(handler, 'chat'):
            messages = [
                 {"role": "system", "content": "You are an expert writing style analyst. Your task is to analyze the provided text and output a concise, structured style guide based on it. Output ONLY the style guide."},
                 {"role": "user", "content": guidance_prompt} # Pass the full prompt as user message
            ]
            chat_response = await handler.chat(messages=messages, model=model)
            # Extract content from chat response (similar logic as in transfer_style)
            if isinstance(chat_response, dict) and 'content' in chat_response:
                 extracted_guidance = chat_response['content']
            elif isinstance(chat_response, object) and hasattr(chat_response, 'content'):
                 extracted_guidance = chat_response.content
            elif isinstance(chat_response, str):
                 extracted_guidance = chat_response
            else:
                 logger.warning(f"Unexpected chat response format during guidance extraction: {type(chat_response)}")
                 extracted_guidance = str(chat_response) # Fallback
        else:
             raise NotImplementedError(f"Handler {provider} supports neither generate_text nor chat.")

        if not extracted_guidance:
            raise ValueError("LLM did not return style guidance.")
        
        logger.info("Successfully extracted style guidance.")
        # Basic cleaning: remove potential markdown fences or leading/trailing whitespace
        cleaned_guidance = extracted_guidance.strip().removeprefix('```').removesuffix('```').strip()
        return cleaned_guidance

    except Exception as e:
        logger.error(f"Error extracting style guidance: {e}", exc_info=True)
        # Re-raise or handle appropriately, maybe return None or raise specific exception
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to extract style guidance: {str(e)}")
# --- End of helper function ---

# --- API Endpoint ---

@router.post("/", response_model=TransferResponse, summary="Perform style transfer with segmentation")
async def perform_style_transfer(request: TransferRequest = Body(...), db: AsyncSession = Depends(get_db)):
    """
    Transfers the style of a source text to generate new text based on a new theme.
    Handles long themes by segmenting the generation process.
    """
    logger.info(f"Received style transfer request. Input type: {request.input_type}, Provider: {request.provider}, Model: {request.model}")

    style_guidance: Optional[str] = None

    try:
        # 1. Determine the style guidance (Stage 1 - unchanged)
        if request.input_type == 'text' or request.input_type == 'file':
            if not request.source_text:
                raise_http_error(status.HTTP_400_BAD_REQUEST, "Source text is required for input type 'text' or 'file'.")
            logger.info("Input type is text/file. Starting Stage 1: Extracting style guidance.")
            try:
                 style_guidance = await _extract_style_guidance(
                     text=request.source_text,
                     provider=request.provider,
                     model=request.model
                 )
                 logger.debug(f"Extracted style_guidance (length: {len(style_guidance)})")
            except Exception as extraction_err:
                 logger.error(f"Failed to extract style guidance from source text: {extraction_err}")
                 raise HTTPException(status_code=500, detail=f"Failed to analyze style from source text: {extraction_err}")

        elif request.input_type == 'analysis':
            if not request.analysis_report_id:
                raise_http_error(status.HTTP_400_BAD_REQUEST, "Analysis report ID is required for input type 'analysis'.")

            logger.info(f"Fetching analysis report with ID: {request.analysis_report_id}")
            report_data = await get_analysis_result(request.analysis_report_id, db)

            if not report_data:
                raise_http_error(status.HTTP_404_NOT_FOUND, f"Analysis report with ID '{request.analysis_report_id}' not found.")

            # --- Extract analysis content as guidance (Keep this logic) --- 
            analysis_content = None
            if isinstance(report_data.get('result'), dict) and report_data['result'].get('deep_analysis_report') is not None:
                 analysis_content = report_data['result']['deep_analysis_report']
            elif isinstance(report_data.get('result'), dict) and report_data['result'].get('analysis_report') is not None:
                analysis_content = report_data['result']['analysis_report']
            elif report_data.get('result') is not None:
                analysis_content = report_data['result']
            else:
                logger.error(f"Could not extract analysis content (guidance) from report ID {request.analysis_report_id}.")
                raise_http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Could not extract analysis guidance from report '{request.analysis_report_id}'.")
                            
            if not isinstance(analysis_content, str):
                 try:
                     style_guidance = json.dumps(analysis_content, ensure_ascii=False, indent=2)
                 except Exception as json_err:
                     logger.error(f"Failed to serialize analysis guidance to JSON: {json_err}. Using raw string representation.")
                     style_guidance = str(analysis_content)
            else:
                style_guidance = analysis_content
            
            style_guidance = style_guidance.strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip()
            if not style_guidance:
                 logger.error(f"Extracted style guidance from report ID {request.analysis_report_id} is empty after processing.")
                 raise_http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Extracted style guidance from analysis report '{request.analysis_report_id}' is empty.")

            logger.debug(f"Using style_guidance from analysis report (length: {len(style_guidance)})")
            # --- End of guidance extraction from report ---
        else:
            raise_http_error(status.HTTP_400_BAD_REQUEST, f"Invalid input_type: {request.input_type}")
        
        if not style_guidance:
             logger.error("Style guidance could not be determined from input.")
             raise HTTPException(status_code=500, detail="Failed to determine style guidance for generation.")

        # === Stage 2: Generate Text using Guidance (with Segmentation) ===
        logger.info(f"Starting Stage 2: Generating text for theme (length: {len(request.new_theme)}) using guidance...")
        
        generated_text: str = ""
        
        # Check if segmentation is needed
        if len(request.new_theme) > SEGMENT_THRESHOLD_CHARS:
            logger.info(f"Theme length exceeds threshold ({SEGMENT_THRESHOLD_CHARS} chars). Applying segmentation.")
            prompt_segments = split_into_paragraphs(request.new_theme)
            logger.info(f"Split theme into {len(prompt_segments)} segments.")
            
            generated_segments = []
            previous_segment_output = "" # Start with empty context

            for i, segment in enumerate(prompt_segments):
                logger.info(f"Processing segment {i+1}/{len(prompt_segments)}...")
                
                # Construct the prompt for this segment, including context from previous segment
                if not previous_segment_output:
                    # First segment prompt
                    current_call_prompt = segment 
                else:
                    # Subsequent segment prompt - instruct to continue
                    current_call_prompt = f"请严格按照之前的风格和语气，自然地衔接下面的内容，继续创作。\n【上文回顾】:\n{previous_segment_output}\n\n【继续创作以下内容】:\n{segment}"
                
                try:
                    # Call the core style transfer function for the current segment's prompt
                    # Note: We pass the *full* context-aware prompt as 'new_content_prompt' now
                    generated_segment = await style_transfer_processor.transfer_style(
                        style_guidance=style_guidance, 
                        new_content_prompt=current_call_prompt, # This contains the context + current segment goal
                        api_provider=request.provider,
                        model=request.model
                    )
                    
                    # Basic cleaning of the generated segment (optional)
                    cleaned_segment = generated_segment.strip()
                    generated_segments.append(cleaned_segment)
                    previous_segment_output = cleaned_segment # Update context for the next iteration
                    logger.info(f"Segment {i+1} generated successfully (length: {len(cleaned_segment)}).")
                
                except Exception as segment_err:
                    logger.error(f"Error generating segment {i+1}: {segment_err}", exc_info=True)
                    # Decide how to handle segment failure: stop, skip, or try to continue?
                    # For now, let's stop and raise an error.
                    raise HTTPException(status_code=500, detail=f"Failed to generate text for segment {i+1}: {str(segment_err)}")

            # Combine the generated segments
            generated_text = "\\n\\n".join(generated_segments) # Join with double newline for paragraph separation
            logger.info(f"All segments generated and combined. Total length: {len(generated_text)}")

        else:
            # Theme is short enough, generate in one go (existing logic)
            logger.info("Theme length is within threshold. Generating text in a single call.")
            generated_text = await style_transfer_processor.transfer_style(
                style_guidance=style_guidance, 
                new_content_prompt=request.new_theme,
                api_provider=request.provider,
                model=request.model
            )
        # === End of Stage 2 ===

        logger.info(f"Style transfer successful. Final result length: {len(generated_text)}")
        return TransferResponse(result=generated_text)

    except HTTPException as http_exc:
        logger.error(f"HTTP Error during style transfer: {http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.exception(f"Error during style transfer: {e}")
        handle_error(e)
        raise HTTPException(status_code=500, detail=f"Style transfer failed: {str(e)}") 