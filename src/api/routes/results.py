"""
API routes for managing and saving analysis results.
"""
import json
import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, status, Body, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import os

from src.utils.logging import logger
from src.utils.error_handler import handle_error, raise_http_error
from src.utils.cache import save_analysis_result, get_analysis_result, get_cache_dir
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.manager import get_db, list_results, get_result_by_result_id, delete_result_record
from src.database.manager import Result as DBResult
from src.database import manager # Ensure manager is imported

# --- Define Cache Directory --- 
# Note: We're keeping this for backward compatibility, but new results will use the unified cache system
try:
    # Go up three levels from src/api/routes/results.py to get project root
    PROJECT_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
except NameError:
    # Fallback for environments where __file__ might not be defined reliably
    PROJECT_ROOT_DIR = Path.cwd()
    logger.warning(f"Could not determine project root from __file__, using cwd: {PROJECT_ROOT_DIR}")

STYLE_ANALYSIS_CACHE_DIR = PROJECT_ROOT_DIR / "data" / "style_analysis_cache"

# Ensure the cache directory exists
try:
    STYLE_ANALYSIS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Ensured style analysis cache directory exists: {STYLE_ANALYSIS_CACHE_DIR}")
except Exception as e:
    logger.error(f"Failed to create style analysis cache directory {STYLE_ANALYSIS_CACHE_DIR}: {e}")
    # Decide if this is a fatal error or if saving should just fail later

# --- Pydantic Model for Saving Request ---
class SaveAnalysisPayload(BaseModel):
    text_summary: str = Field(..., description="Summary or beginning of the analyzed text")
    result: Any = Field(..., description="The analysis result (can be string or dict/list)")
    provider: Optional[str] = Field(None, description="API Provider used")
    model: Optional[str] = Field(None, description="Model used")
    timestamp: str = Field(..., description="Timestamp of the analysis (ISO format)")
    analysis_type: str = Field("literature_v2", description="Type of analysis performed")
    original_text: Optional[str] = Field(None, description="The full original text that was analyzed")

# --- Results Model (Pydantic, for API response) ---
class ResultResponse(BaseModel): 
    result_id: str
    name: Optional[str] = None
    type: str 
    timestamp: datetime.datetime # 修正：使用 datetime.datetime 类
    source_info: Optional[str] = None
    model_info: Optional[str] = None
    file_path: str
    tags: Optional[str] = None

    class Config: # 允许从 ORM 模型创建
        # orm_mode = True # pydantic v1 syntax
        from_attributes = True # 修正：使用 pydantic v2 syntax

# --- Router Definition ---
router = APIRouter(prefix="/results", tags=["results"])

# --- 正确添加 GET / 路由 --- 
@router.get("", response_model=List[ResultResponse], summary="Get list of all analysis results metadata")
async def get_results_list(limit: int = 100, offset: int = 0, db: AsyncSession = Depends(get_db)):
    """
    Retrieves a list of analysis results metadata from the database using the function from manager.py.
    """
    logger.info(f"Request received to list analysis results (limit={limit}, offset={offset})")
    try:
        db_results: List[DBResult] = await list_results(db, limit=limit, offset=offset)
        # 直接使用 Pydantic 模型的 orm_mode 进行转换
        return db_results # FastAPI 会自动处理转换
    except Exception as e:
        logger.error(f"Error listing analysis results: {e}", exc_info=True)
        raise_http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to list analysis results: {str(e)}")

# --- 添加 Ping 测试路由 ---
@router.get("/ping", status_code=status.HTTP_200_OK, include_in_schema=False)
async def ping_results_router():
    return {"message": "pong from results router"}

# --- API Endpoints ---

@router.get("/literature/{result_id}", response_model=Dict[str, Any], summary="Get literature analysis result")
async def get_literature_analysis_result_endpoint(result_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieves a specific literature analysis result by ID.
    """
    logger.info(f"Request received to get literature analysis result: {result_id}")
    
    try:
        # First try to get from the new unified cache
        result = await get_analysis_result(result_id, db)
        
        # If not found and might be legacy format, check old directory
        if result is None and STYLE_ANALYSIS_CACHE_DIR.exists():
            legacy_path = STYLE_ANALYSIS_CACHE_DIR / f"{result_id}.json"
            if legacy_path.exists():
                try:
                    with open(legacy_path, 'r', encoding='utf-8') as f:
                        result = json.load(f)
                    # For legacy results, ensure it has an id field
                    result['id'] = result_id
                    logger.info(f"Retrieved legacy literature analysis result: {result_id}")
                except Exception as e:
                    logger.error(f"Error reading legacy result file {legacy_path}: {e}", exc_info=True)
        
        if result is None:
            raise_http_error(status.HTTP_404_NOT_FOUND, f"Analysis result with ID {result_id} not found")
            
        return result
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error retrieving literature analysis result {result_id}: {e}", exc_info=True)
        raise_http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to retrieve analysis result: {str(e)}")

@router.get("/text-analysis/{result_id}", response_model=Dict[str, Any], summary="Get text analysis result")
async def get_text_analysis_result_endpoint(result_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieves a specific text analysis result by ID.
    """
    logger.info(f"Request received to get text analysis result: {result_id}")
    
    try:
        # Get from the unified cache
        result = await get_analysis_result(result_id, db)
        
        if result is None:
            raise_http_error(status.HTTP_404_NOT_FOUND, f"Text analysis result with ID {result_id} not found")
            
        return result
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error retrieving text analysis result {result_id}: {e}", exc_info=True)
        raise_http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to retrieve analysis result: {str(e)}")

@router.get("/style/{result_id}", response_model=Dict[str, Any], summary="Get style transfer result")
async def get_style_transfer_result_endpoint(result_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieves a specific style transfer result by ID.
    """
    logger.info(f"Request received to get style transfer result: {result_id}")
    
    try:
        # Get from the unified cache
        result = await get_analysis_result(result_id, db)
        
        if result is None:
            raise_http_error(status.HTTP_404_NOT_FOUND, f"Style transfer result with ID {result_id} not found")
            
        return result
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error retrieving style transfer result {result_id}: {e}", exc_info=True)
        raise_http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to retrieve analysis result: {str(e)}")

@router.post("/save-literature", summary="Save literature analysis result")
async def save_literature_analysis(payload: SaveAnalysisPayload = Body(...), db: AsyncSession = Depends(get_db)):
    """
    Receives literature analysis results and saves them using the unified cache system and DB.
    Maintains backward compatibility for saving to the old directory.
    """
    logger.info(f"Received request to save {payload.analysis_type} analysis result.")

    try:
        # Convert payload to dictionary
        data = payload.dict()
        
        # Parse result if it's a JSON string (optional improvement)
        if isinstance(payload.result, str):
            try:
                parsed_result = json.loads(payload.result)
                data['result'] = parsed_result
            except json.JSONDecodeError:
                logger.warning("Result field is a string but not valid JSON. Saving as string.")
            except Exception as e:
                logger.error(f"Unexpected error parsing result JSON: {e}")
        
        # Save using the updated function signature, passing db
        result_id = await save_analysis_result('literature', data, db)
        
        if not result_id:
            logger.error("Failed to save literature result (save_analysis_result returned None)")
            raise HTTPException(status_code=500, detail="Failed to save literature analysis result")
        
        # --- Backward Compatibility: Save to old directory (Keep this part as is) ---
        if STYLE_ANALYSIS_CACHE_DIR.exists():
            try:
                # Sanitize model/provider names for filename
                safe_provider = str(payload.provider).replace("/", "_").replace("\\", "_") if payload.provider else "unknown_provider"
                safe_model = str(payload.model).replace("/", "_").replace("\\", "_") if payload.model else "unknown_model"
                
                # Create filename with error handling
                try:
                    timestamp_str = str(payload.timestamp).replace(":", "-").replace(".", "-")  # Basic sanitization
                    filename = f"{timestamp_str}_{safe_provider}_{safe_model}.json"
                except Exception as e:
                    logger.warning(f"Error formatting timestamp for filename: {e}")
                    # Fallback to current timestamp
                    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                    filename = f"{timestamp_str}_{safe_provider}_{safe_model}.json"
                
                file_path = STYLE_ANALYSIS_CACHE_DIR / filename
                
                # Save data as JSON
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Also saved analysis result to legacy path: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to save to legacy path, but saved to unified cache: {e}")
        # --------------------------------------------------------------------------
        
        logger.info(f"Successfully saved literature analysis result with ID: {result_id}")
        return {"status": "success", "message": "Analysis result saved.", "id": result_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving literature analysis result: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save analysis result: {str(e)}")

@router.post("/save-text-analysis", summary="Save text analysis result")
async def save_text_analysis(payload: Dict[str, Any] = Body(...), db: AsyncSession = Depends(get_db)):
    """
    Receives text analysis results and saves them using the unified cache system and records metadata to DB.
    """
    logger.info("Received request to save text analysis result.")

    try:
        # Verify payload is a dictionary
        if not isinstance(payload, dict):
            logger.error(f"Invalid payload type: {type(payload)}")
            raise HTTPException(status_code=400, detail="Payload must be a JSON object")
        
        # Make a copy to avoid modifying the original
        payload_copy = payload.copy()
        
        # Add timestamp if not present (cache function also does this, but good practice here too)
        if "timestamp" not in payload_copy:
            payload_copy["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Save to the unified cache system, passing the db session
        # Make sure to await the async function now
        result_id = await save_analysis_result('text', payload_copy, db)
        
        if not result_id:
            logger.error("Failed to save analysis result (save_analysis_result returned None)")
            raise HTTPException(status_code=500, detail="Failed to save analysis result")
        
        logger.info(f"Successfully saved text analysis result with ID: {result_id}")
        return {"status": "success", "message": "Text analysis result saved.", "id": result_id}

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error saving text analysis result: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save text analysis result: {str(e)}")

@router.post("/save-style", summary="Save style transfer result")
async def save_style_transfer(payload: Dict[str, Any] = Body(...), db: AsyncSession = Depends(get_db)):
    """
    Receives style transfer results and saves them using the unified cache system and DB.
    """
    logger.info("Received request to save style transfer result.")

    try:
        # Verify payload is a dictionary
        if not isinstance(payload, dict):
            logger.error(f"Invalid payload type: {type(payload)}")
            raise HTTPException(status_code=400, detail="Payload must be a JSON object")
        
        # Make a copy to avoid modifying the original
        payload_copy = payload.copy()
        
        # Add timestamp if not present (cache function also does this)
        if "timestamp" not in payload_copy:
            payload_copy["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Save to the unified cache system (which now includes DB logging)
        # Pass the db session
        result_id = await save_analysis_result('style', payload_copy, db)
        
        if not result_id:
            logger.error("Failed to save style transfer result (save_analysis_result returned None)")
            raise HTTPException(status_code=500, detail="Failed to save style transfer result")
        
        logger.info(f"Successfully saved style transfer result with ID: {result_id}")
        return {"status": "success", "message": "Style transfer result saved.", "id": result_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving style transfer result: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save style transfer result: {str(e)}")

# --- 新增：删除结果路由 --- 
@router.delete("/{result_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an analysis result")
async def delete_analysis_result(result_id: str, db: AsyncSession = Depends(get_db)):
    """
    Deletes an analysis result by its ID, including the database record and the cached file.
    """
    logger.info(f"Request received to delete analysis result: {result_id}")
    
    file_deleted = False
    db_record_deleted = False
    file_path_to_delete = None
    module_type = None # 需要获取 module_type 来确定缓存目录

    try:
        # 1. 获取数据库记录以找到文件路径和类型
        record = await get_result_by_result_id(db, result_id)
        
        if not record:
            logger.warning(f"Result with ID {result_id} not found in database for deletion.")
            # 即使记录不存在，也可能尝试删除孤立文件（如果知道类型），但通常返回404
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
        
        module_type = record.type
        # 假设 file_path 存储的是相对于 cache 目录的路径或完整路径
        # 我们需要更可靠地确定文件路径。save_analysis_result 使用 get_cache_dir
        cache_dir = get_cache_dir(module_type) # 获取对应模块的缓存根目录
        if cache_dir:
             # result_id 通常就是文件名（不含扩展名）
            file_path_to_delete = cache_dir / f"{result_id}.json"
        else:
            logger.warning(f"Could not determine cache directory for module type: {module_type}")
            # 可能需要从 record.file_path 解析，但这不够健壮
            # 暂时跳过文件删除，只删数据库记录

        # 2. 尝试删除文件 (如果路径确定)
        if file_path_to_delete and file_path_to_delete.exists():
            try:
                os.remove(file_path_to_delete)
                file_deleted = True
                logger.info(f"Successfully deleted cache file: {file_path_to_delete}")
            except OSError as e:
                logger.error(f"Error deleting cache file {file_path_to_delete}: {e}", exc_info=True)
                # 文件删除失败，但我们仍然继续删除数据库记录
        elif file_path_to_delete:
             logger.warning(f"Cache file not found at expected location: {file_path_to_delete}")
             # 文件本就不存在，也算作文件删除"成功"（或无需操作）
             file_deleted = True # Consider it done if not found

        # 3. 删除数据库记录
        db_record_deleted = await delete_result_record(db, result_id)
        
        # 根据删除结果返回 (204 NO CONTENT 表示成功，无需响应体)
        if db_record_deleted:
             # 即使文件删除失败或未找到，只要DB记录删除了，就认为操作成功
             pass # 成功时无需返回任何内容 (HTTP 204)
        else:
            # delete_result_record 内部已处理未找到的情况，理论上不应到这里
            # 但以防万一
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete database record after potentially deleting file.")

    except HTTPException:
        raise # 重新抛出已知的 HTTP 异常
    except Exception as e:
        logger.error(f"Error deleting analysis result {result_id}: {e}", exc_info=True)
        # 根据错误类型判断是否需要回滚文件删除？(通常不需要)
        raise_http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to delete analysis result: {str(e)}") 

# --- Add this section in src/api/routes/results.py ---
# (Make sure necessary imports like Depends, Body, manager are present)
from src.database import manager # Ensure manager is imported

class RenamePayload(BaseModel):
    new_name: str = Field(..., min_length=1, description="The new name for the result record")

@router.patch("/{result_id}/rename", status_code=status.HTTP_200_OK, summary="Rename an analysis result")
async def rename_analysis_result(
    result_id: str,
    payload: RenamePayload = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Updates the name of a specific analysis result record in the database.
    """
    logger.info(f"Request received to rename result {result_id} to '{payload.new_name}'")
    try:
        success = await manager.update_result_name(db, result_id, payload.new_name)
        if success:
            logger.info(f"Successfully renamed result {result_id}")
            return {"status": "success", "message": "Result renamed successfully."}
        else:
            # manager.update_result_name returns False if record not found
            logger.warning(f"Result record with ID {result_id} not found for renaming.")
            raise_http_error(status.HTTP_404_NOT_FOUND, f"Result record with ID {result_id} not found.")
    except Exception as e:
        # Catch potential errors from update_result_name or other issues
        logger.exception(f"Error renaming result {result_id}: {e}") # Use logger.exception for stack trace
        # Avoid raising generic 500 if it's a known DB issue handled by manager's raise
        # If manager re-raises, FastAPI's exception handlers should catch it.
        # If it's another error, raise a 500.
        if not isinstance(e, HTTPException): # Avoid re-raising HTTPExceptions
             handle_error(e) # Use your generic error handler if appropriate
             raise_http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to rename result: {str(e)}")
        else:
             raise e # Re-raise HTTPException

# --- End of added section --- 