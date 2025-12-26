"""
API routes specifically for V2 multi-dimensional literature analysis.
"""
from fastapi import APIRouter, HTTPException, status, Body
from typing import List, Dict, Any

from src.api.models.analysis import LiteratureAnalysisRequest, LiteratureAnalysisResponse # Reuse models
from src.core.literature_analyzer import (
    load_detailed_literature_template, 
    build_detailed_literature_prompt 
)
from src.providers.factory import get_handler
from src.utils.logging import logger
from src.utils.error_handler import handle_error, raise_http_error

# --- Router Definition ---
router = APIRouter(prefix="/literature-analysis", tags=["literature-analysis"])

# --- API Endpoints ---

@router.get("/template-structure", response_model=Dict[str, Any], summary="获取详细文学分析模板结构 (V2)")
async def get_detailed_literature_structure_v2():
    """Get the structure of the V2 multi-dimensional literature analysis template."""
    template_structure = load_detailed_literature_template()
    if template_structure is None:
        raise_http_error(status.HTTP_404_NOT_FOUND, "Detailed literature template (V2) not found or failed to load.")
    return template_structure

@router.post("/analyze", response_model=LiteratureAnalysisResponse, summary="执行详细文学分析 (V2)")
async def perform_detailed_literature_analysis_v2(request: LiteratureAnalysisRequest = Body(...)):
    """执行详细文学分析 (使用 V2 模板)。"""
    logger.info(f"Received detailed literature analysis V2 request: Provider='{request.provider}', Model='{request.model}', "
                   f"Selected Dimensions Count={len(request.selected_dimensions)}")
    
    # --- Optional: Check Cache First --- 
    # cache_key_args = (request.provider, request.model, request.text, tuple(sorted(request.selected_dimensions)))
    # cached_result = cache.get(*cache_key_args)
    # if cached_result and 'result' in cached_result:
    #    logger.info("Cache hit for detailed literature analysis!")
    #    return LiteratureAnalysisResponse(result=cached_result['result'])
    # logger.info("Cache miss for detailed literature analysis.")
    # ------------------------------------

    try:
        # 1. Load the V2 template 
        v2_template = load_detailed_literature_template()
        if not v2_template:
            raise_http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to load detailed literature template (V2) for analysis.")
            
        # 2. Build prompt using V2 logic
        prompt = build_detailed_literature_prompt(request.text, request.selected_dimensions, v2_template) 
        
        # 3. Call Handler
        handler = get_handler(request.provider)
        logger.info(f"Sending V2 analysis request to Provider '{request.provider}' (Model: '{request.model}')...")
        
        # Actually call the handler to generate text
        analysis_result_text = await handler.generate_text(prompt, model=request.model)
        
        logger.info(f"Successfully obtained V2 analysis result from '{request.provider}'.")
        
        # --- Optional: Set Cache --- 
        # cache_value = {"result": analysis_result_text, "provider": request.provider, "model": request.model}
        # cache.set(cache_value, *cache_key_args)
        # ---------------------------

        # Return the actual result
        return LiteratureAnalysisResponse(result=analysis_result_text)
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.exception(f"Error executing detailed literature analysis V2: {e}")
        handle_error(e) # Use centralized error handling 