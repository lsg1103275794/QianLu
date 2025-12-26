"""""
API routes for managing and viewing results (Data Terminal).
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
import os
from pathlib import Path
import json
from pydantic import BaseModel, Field
from datetime import datetime

from src.database.manager import get_db, list_results, Result as DbResult, update_result_name
from src.utils.cache import get_analysis_result
from src.utils.logging import logger

# --- Pydantic Models --- 

class ResultResponse(BaseModel):
    id: int
    result_id: str
    name: Optional[str] = None
    type: str
    timestamp: datetime
    source_info: Optional[str] = None
    model_info: Optional[str] = None
    file_path: str
    tags: Optional[str] = None

    class Config:
        from_attributes = True 

class RenameRequest(BaseModel):
    new_name: str = Field(..., min_length=1, max_length=255)

class UpdateContentRequest(BaseModel):
    content: str # Expecting the new text content

# --- Router Definition ---
router = APIRouter(
    prefix="/results", # Using /results as the endpoint prefix
    tags=["Data Terminal"], # Tag for API docs
    dependencies=[Depends(get_db)] # Ensures all routes in this router get a DB session
)

# Get project root directory (consider moving to a config file or shared util)
try:
    PROJECT_ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
except NameError:
    PROJECT_ROOT_DIR = Path.cwd()

# --- API Endpoints ---

@router.get("/", response_model=List[ResultResponse], summary="List all result metadata")
async def get_all_results(
    db: AsyncSession = Depends(get_db),
    limit: int = 100, # Add pagination parameters
    offset: int = 0
):
    """Retrieve a list of all stored result metadata, ordered by most recent first."""
    logger.info(f"Received request to list results (limit={limit}, offset={offset})")
    try:
        results_db = await list_results(db, limit=limit, offset=offset)
        # Pydantic models will automatically convert the list of DbResult objects
        return results_db 
    except Exception as e:
        logger.exception(f"Error fetching results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve results: {str(e)}"
        )

# --- Add GET Endpoint for specific result --- 
@router.get("/{result_id}", response_model=Dict[str, Any], summary="Get details of a specific result")
async def get_result_detail(
    result_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves the full content of a specific analysis result by its ID."""
    logger.info(f"Received request to get details for result ID: {result_id}")
    try:
        # Use the function from cache.py which now reads from DB/file
        result_content = await get_analysis_result(result_id, db)
        if result_content is None:
            logger.warning(f"Result content not found for ID: {result_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result content not found")
        
        logger.info(f"Successfully retrieved details for result ID: {result_id}")
        return result_content # Return the dictionary content
        
    except HTTPException:
        raise # Re-raise specific HTTP exceptions
    except Exception as e:
        logger.exception(f"Error fetching result details for {result_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve result details: {str(e)}"
        )
# -----------------------------------------

# --- Endpoint to rename a result ---
@router.put("/{result_id}/rename", status_code=status.HTTP_200_OK, summary="Rename an analysis result")
async def rename_result(
    result_id: str,
    request_body: RenameRequest, # Expect RenameRequest model in the body
    db: AsyncSession = Depends(get_db)
):
    """Renames a specific analysis result."""
    new_name = request_body.new_name # Extract new_name from the request body
    logger.info(f"Received request to rename result {result_id} to '{new_name}'")
    try:
        success = await update_result_name(db, result_id, new_name)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
        return {"status": "success", "message": "Result renamed successfully."}
    except Exception as e:
        logger.exception(f"Error renaming result {result_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rename result: {str(e)}"
        )

# --- Add DELETE Endpoint --- 
@router.delete("/{result_id}", status_code=status.HTTP_200_OK, summary="Delete an analysis result")
async def delete_result(
    result_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Deletes a result record from the database and its associated file."""
    logger.info(f"Attempting to delete result with ID: {result_id}")
    
    # 1. Find the record in the database
    stmt = select(DbResult).where(DbResult.result_id == result_id)
    db_result = await db.execute(stmt)
    record = db_result.scalar_one_or_none()

    if not record:
        logger.warning(f"Result record with ID '{result_id}' not found for deletion.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    file_path_relative = record.file_path
    record_name = record.name # For logging

    # 2. Delete the database record
    try:
        await db.delete(record)
        await db.commit()
        logger.info(f"Successfully deleted database record for {result_id} ('{record_name}')")
    except Exception as db_err:
        await db.rollback()
        logger.error(f"Failed to delete database record for {result_id}: {db_err}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error during deletion")

    # 3. Delete the associated file
    if file_path_relative:
        try:
            absolute_file_path = PROJECT_ROOT_DIR / file_path_relative
            if absolute_file_path.is_file():
                absolute_file_path.unlink()
                logger.info(f"Successfully deleted associated file: {absolute_file_path}")
            else:
                logger.warning(f"Associated file not found, but DB record deleted: {absolute_file_path}")
        except Exception as file_err:
            # Log the error but don't fail the request, as DB record is already deleted
            logger.error(f"Failed to delete associated file {absolute_file_path} for deleted record {result_id}: {file_err}", exc_info=True)
            # Optionally return a specific message indicating partial success
            return {"status": "warning", "message": "Database record deleted, but failed to delete associated file.", "id": result_id}
    else:
        logger.warning(f"No file path associated with deleted record {result_id}. Only DB record deleted.")

    return {"status": "success", "message": "Result deleted successfully.", "id": result_id}

# --- Add PUT Endpoint for updating content --- 
@router.put("/{result_id}/content", status_code=status.HTTP_200_OK, summary="Update the content of a result file")
async def update_result_content(
    result_id: str,
    request_body: UpdateContentRequest,
    db: AsyncSession = Depends(get_db)
):
    """Updates the primary text content within the result's JSON file."""
    new_content = request_body.content
    logger.info(f"Received request to update content for result ID: {result_id}")

    # 1. Find the record in the database to get the file path
    stmt = select(DbResult).where(DbResult.result_id == result_id)
    db_result = await db.execute(stmt)
    record = db_result.scalar_one_or_none()

    if not record:
        logger.warning(f"Result record with ID '{result_id}' not found for content update.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result record not found")

    if not record.file_path:
        logger.error(f"Result record {result_id} found, but file_path is missing. Cannot update content.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="File path missing for result")

    absolute_file_path = PROJECT_ROOT_DIR / record.file_path
    logger.info(f"Attempting to update content in file: {absolute_file_path}")

    if not absolute_file_path.is_file():
        logger.error(f"Result file not found at path for update: {absolute_file_path}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result file not found")

    # 2. Read the existing JSON file
    try:
        with open(absolute_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as json_err:
        logger.error(f"Failed to decode JSON from result file {absolute_file_path} for update: {json_err}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to read existing result file")
    except Exception as read_err:
        logger.error(f"Failed to read result file {absolute_file_path} for update: {read_err}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to read existing result file")

    # 3. Update the relevant field(s) with the new content
    #    Try updating common fields where the main text might reside.
    updated = False
    potential_keys = ['result', 'content', 'text', 'analysis_result', 'output', 'output_text', 'summary', 'generated_text']
    for key in potential_keys:
        if key in data:
            logger.debug(f"Updating key '{key}' in {result_id}")
            data[key] = new_content
            updated = True
            # break # Option: Stop after updating the first found key?
                     # Let's update all found keys for now.

    if not updated:
        logger.warning(f"No standard content key found in {result_id} to update. File not modified.")
        # Decide if this is an error or just a warning. Let's return success but log a warning.
        # Alternatively, could raise an HTTPException here.
        # raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not find standard content field to update")

    # 4. Write the modified data back to the JSON file
    try:
        with open(absolute_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2) # Use indent for readability
        logger.info(f"Successfully updated content for result ID: {result_id} in file: {absolute_file_path}")
    except Exception as write_err:
        logger.error(f"Failed to write updated content to file {absolute_file_path}: {write_err}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save updated result file")

    return {"status": "success", "message": "Result content updated successfully.", "id": result_id}

# --- Placeholder for future endpoints --- 
# @router.get("/types", ...) - Get distinct result types 