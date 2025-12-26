"""
File handling API routes.
"""
import os
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
import uuid
# Add imports for file parsing libraries
import fitz # PyMuPDF
import docx
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

from src.utils.logging import logger
# from backend_main import UPLOAD_DIR_MAIN # <-- Remove this import
from src.utils.config import UPLOAD_DIR # <-- Import from correct config file
from src.utils import file_utils # Import the file utilities

router = APIRouter(tags=["files"])
logger.debug("### files.py: APIRouter object created successfully.")

# --- 简单的测试路由 --- 
@router.get("/test-files", summary="Test if files router is registered")
async def test_files_router():
    logger.info("===> Received request for /test-files")
    return {"message": "Files router is working!"}

# --- Helper function to extract text from EPUB --- 
def extract_text_from_epub(file_path: Path) -> str:
    try:
        book = epub.read_epub(file_path)
        content = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_body_content(), 'lxml')
            # Get text, strip leading/trailing whitespace from each line, join with space
            text = ' '.join(line.strip() for line in soup.stripped_strings)
            if text:
                content.append(text)
        return "\n\n".join(content) # Join sections with double newline
    except Exception as e:
        logger.error(f"Error extracting text from EPUB {file_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not process EPUB file: {e}")

# --- 获取文件内容的真实逻辑 (增强版) --- 
@router.get("/file-content", response_class=PlainTextResponse, summary="Get text content of an uploaded file")
async def get_file_content(file_path: str = Query(..., description="The unique filename stored on the server.")):
    logger.info(f"Received request to get content for file_path: {file_path}")

    if not file_path or ".." in file_path or "/" in file_path or "\\" in file_path:
        logger.warning(f"Attempted to access invalid file path: {file_path}")
        raise HTTPException(status_code=400, detail="Invalid file path specified.")

    try:
        full_path = UPLOAD_DIR / file_path
        safe_full_path_repr = repr(str(full_path))
        logger.info(f"Attempting to read file content from: {safe_full_path_repr}")

        if not full_path.is_file() or not str(full_path.resolve()).startswith(str(UPLOAD_DIR.resolve())):
            logger.error(f"File not found or path traversal attempt: {safe_full_path_repr}")
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

        file_ext = full_path.suffix.lower()
        content = ""

        try:
            if file_ext == '.pdf':
                logger.debug(f"Reading PDF file: {safe_full_path_repr}")
                with fitz.open(full_path) as doc:
                    content = "\n".join(page.get_text() for page in doc)
            elif file_ext == '.docx':
                logger.debug(f"Reading DOCX file: {safe_full_path_repr}")
                doc = docx.Document(full_path)
                content = "\n".join(para.text for para in doc.paragraphs)
            elif file_ext == '.epub':
                 logger.debug(f"Reading EPUB file: {safe_full_path_repr}")
                 content = extract_text_from_epub(full_path)
            elif file_ext in ['.txt', '.md']: # Treat .md as plain text for now
                logger.debug(f"Reading text file ({file_ext}): {safe_full_path_repr}")
                content = full_path.read_text(encoding='utf-8')
            else:
                logger.warning(f"Unsupported file type requested for text extraction: {file_ext}")
                raise HTTPException(
                    status_code=415, 
                    detail=f"Cannot extract text content: Unsupported file type '{file_ext}' for file '{file_path}'."
                )
            
            logger.info(f"Successfully extracted text content ({len(content)} chars) from {safe_full_path_repr}")
            return PlainTextResponse(content=content)

        except UnicodeDecodeError:
             # This might happen for .txt/.md if they are not UTF-8
             logger.warning(f"File {safe_full_path_repr} is not valid UTF-8 text.")
             raise HTTPException(
                 status_code=415, 
                 detail=f"Cannot get text content: File '{file_path}' is not a valid UTF-8 encoded text file."
             )
        except Exception as read_err:
            logger.error(f"Error reading/processing file {safe_full_path_repr} (type: {file_ext}): {read_err}")
            # Provide more specific error if possible, e.g., for corrupted files
            detail_msg = f"Could not read or process file content: {file_path}. Error: {read_err}"
            status_code = 500
            if "encrypted" in str(read_err).lower(): # Example: Check for encrypted PDF error
                 detail_msg = f"Could not process file: '{file_path}' might be password-protected or encrypted."
                 status_code = 400 # Bad request, user needs to provide unencrypted file
            elif "is not a zip file" in str(read_err).lower(): # Example: Corrupted DOCX
                 detail_msg = f"Could not process file: '{file_path}' seems corrupted or is not a valid DOCX file."
                 status_code = 400
                 
            raise HTTPException(status_code=status_code, detail=detail_msg)

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error in get_file_content for {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Server error retrieving file content.")

# --- 原来的代码已完全移除 (注释掉，以防万一需要参考) --- 
# @router.get("/file_content", summary="Get content of an uploaded file - DEBUG")
# async def get_file_content_debug(file_path: str = Query(...)): # 保持参数签名以匹配路由
#     logger.info(f"===> Received request for /api/file-content (DEBUG), file_path param: {file_path}")
#     # 直接返回成功响应，不进行任何文件操作
#     return JSONResponse(content={
#         "status": "success_debug", 
#         "file_path": file_path,
#         "content": "This is dummy content from simplified get_file_content."
#         }, 
#         status_code=200
#     )

# --- 原来的代码已完全移除 --- 

# Ensure UPLOAD_DIR exists
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/files", tags=["files"])

MAX_FILE_SIZE = 50 * 1024 * 1024 # 50 MB
ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx", ".epub", ".md", ".yaml", ".json"} # Define allowed extensions

@router.post("/upload", summary="Upload a file and get its server path")
async def upload_file(file: UploadFile = File(...)):
    # (Keep the existing /upload endpoint if it's used elsewhere)
    # ... implementation similar to backend_main.py ...
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid file type: {file_ext}")
    
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = UPLOAD_DIR / unique_filename
    try:
        actual_size = 0
        with open(file_path, "wb") as buffer:
             while content := await file.read(1024 * 1024):
                 actual_size += len(content)
                 if actual_size > MAX_FILE_SIZE:
                     buffer.close()
                     file_path.unlink()
                     raise HTTPException(status_code=413, detail="File size limit exceeded")
                 buffer.write(content)
        logger.info(f"File '{file.filename}' uploaded to {unique_filename}")
        return {"file_path": unique_filename, "original_filename": file.filename}
    except Exception as e:
        logger.error(f"Failed to upload file {file.filename}: {e}")
        if file_path.exists(): file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Could not save file")

# --- NEW ENDPOINT --- 
@router.post("/upload-and-extract", summary="Upload file and extract text content")
async def upload_and_extract(file: UploadFile = File(...)):
    """
    Receives a file, saves it temporarily, extracts text content using file_utils,
    deletes the temporary file, and returns the extracted text.
    """
    logger.info(f"Received request for /upload-and-extract: {file.filename}")
    file_ext = Path(file.filename).suffix.lower()
    # Basic check, rely more on file_utils detection later
    # if file_ext not in ALLOWED_EXTENSIONS:
    #     logger.warning(f"File type {file_ext} might not be directly supported by basic check.")
        # raise HTTPException(status_code=400, detail=f"Initial check failed for file type: {file_ext}")

    # Save temporarily to use file_utils.load_file_content which needs a path
    temp_dir = UPLOAD_DIR / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_filename = f"temp_{uuid.uuid4()}{file_ext}"
    temp_file_path = temp_dir / temp_filename
    temp_file_path_for_response = "" # Initialize
    
    try:
        actual_size = 0
        with open(temp_file_path, "wb") as buffer:
             while content := await file.read(1024 * 1024): # Read in chunks
                 actual_size += len(content)
                 if actual_size > MAX_FILE_SIZE:
                     buffer.close()
                     temp_file_path.unlink(missing_ok=True)
                     logger.warning(f"Upload failed: File {file.filename} exceeds size limit.")
                     raise HTTPException(status_code=413, detail="File size limit exceeded")
                 buffer.write(content)
        logger.info(f"File '{file.filename}' saved temporarily to {temp_filename}")

        # Store the relative path for the response
        temp_file_path_for_response = str(Path("temp") / temp_filename)

        # Extract content using file_utils
        # Pass the logger instance to the utility function
        extracted_text = file_utils.load_file_content(temp_file_path, logger) 
        logger.info(f"Text extraction completed for '{temp_filename}'. Result length: {len(extracted_text)}")

    except HTTPException as http_exc:
         logger.error(f"HTTP exception during upload/processing of {file.filename}: {http_exc.detail}")
         raise http_exc # Re-raise HTTP exceptions
    except Exception as e:
        logger.exception(f"Error during upload or extraction for {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Server error during file processing: {str(e)}")
    finally:
        # Ensure temporary file is deleted
        if temp_file_path.exists():
            try:
                # temp_file_path.unlink() # Temporarily commented out for testing async task access
                # logger.info(f"Temporary file deleted: {temp_filename}")
                logger.info(f"Temporary file *not* deleted (for testing): {temp_filename}") # Logging that it's not deleted
                pass
            except OSError as e:
                logger.error(f"Error deleting temporary file {temp_filename}: {e}")

    # Check if extraction returned an error/warning message from file_utils
    if extracted_text.startswith("错误:"):
         logger.error(f"Failed to extract text from {file.filename}. Reason: {extracted_text}")
         # Return a specific error code? 400 Bad Request seems appropriate
         raise HTTPException(status_code=400, detail=extracted_text)
    elif extracted_text.startswith("警告:"):
         logger.warning(f"Warning during text extraction from {file.filename}: {extracted_text}")
         # Return success but include the warning? Or let caller handle based on content?
         # For now, return the text including the warning.
         pass 

    logger.info(f"Successfully extracted text from '{file.filename}'. Returning content and path.")
    return {
        "extracted_text": extracted_text,
        "original_filename": file.filename,
        "file_path": temp_file_path_for_response # Added file_path to the response
    }

# Add other file-related endpoints if needed (e.g., delete file, get file content)