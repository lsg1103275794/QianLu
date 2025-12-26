# src/api/routes/ui_state.py
from fastapi import APIRouter, HTTPException, status, Body, Path as FastApiPath
from typing import Dict, Any, Optional

from src.utils.logging import logger
from src.utils.ui_state import get_ui_state, save_ui_state

router = APIRouter(prefix="/ui-state", tags=["ui-state"])

@router.get("/{page_key}", response_model=Optional[Dict[str, Any]], summary="Get UI state for a specific page")
async def get_page_ui_state(page_key: str = FastApiPath(..., description="Identifier for the page/module (e.g., 'text-analysis')")):
    logger.debug(f"API request to get UI state for: {page_key}")
    state = await get_ui_state(page_key)
    if state is None:
        # 返回 200 和 null 体，表示没有保存过状态，前端应使用默认值
        logger.debug(f"No saved UI state found for {page_key}, returning null.")
        return None
    return state

@router.post("/{page_key}", status_code=status.HTTP_204_NO_CONTENT, summary="Save UI state for a specific page")
async def save_page_ui_state(
    state: Dict[str, Any] = Body(...),
    page_key: str = FastApiPath(..., description="Identifier for the page/module")
):
    logger.debug(f"API request to save UI state for: {page_key} with data: {state}") # Log received state
    success = await save_ui_state(page_key, state)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save UI state.")
    # 成功时返回 204 No Content 