"""
Main application entry point.
"""
import uvicorn
from fastapi import FastAPI, Request, UploadFile, File as FastApiFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from src.utils.logging import logger
from src.api.routes import (
    tasks, 
    analysis, 
    settings, 
    files, 
    providers, 
    chat, 
    chat_history, 
    templates,
    literature_analysis,
    results,
    transfer,
    data_terminal,
    ui_state,
    report_generator_api,
    hot_topics_routes
)
from src.utils.startup import startup_event, shutdown_event
from src.database.manager import init_db
from pathlib import Path
import uuid
from src.utils.config import UPLOAD_DIR
from src.providers.factory import initialize_handlers

# --- 新增：确定前端静态文件路径 ---
PROJECT_ROOT = Path(__file__).resolve().parent # 修改：假设 backend_main.py 在项目根目录
FRONTEND_DIST_DIR = PROJECT_ROOT / "frontend" / "dist"

# --- Constants ---
ALLOWED_EXTENSIONS_MAIN = {".txt", ".pdf", ".docx", ".epub", ".md"}
MAX_FILE_SIZE = 50 * 1024 * 1024 # 50 MB

def create_app() -> FastAPI:
    """Creates and configures the FastAPI application instance."""
    logger.info("Creating FastAPI application instance...")
    app = FastAPI(
        title="字琢 API",
        description="字琢应用程序的 API",
        version="1.0.0"
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers from src.api.routes
    logger.info("Including routers...")
    app.include_router(tasks.router)
    app.include_router(analysis.router, prefix="/api")
    app.include_router(literature_analysis.router, prefix="/api")
    app.include_router(settings.router, prefix="/api")
    app.include_router(files.router, prefix="/api")
    app.include_router(providers.提供商路由, prefix="/api")
    app.include_router(chat.聊天路由, prefix="/api")
    app.include_router(chat_history.router, prefix="/api")
    app.include_router(templates.router, prefix="/api")
    app.include_router(results.router, prefix="/api")
    app.include_router(transfer.router, prefix="/api")
    app.include_router(data_terminal.router, prefix="/api")
    app.include_router(ui_state.router, prefix="/api")
    app.include_router(report_generator_api.router, prefix="/api/v1/reports", tags=["研报生成"])
    app.include_router(hot_topics_routes.router, prefix="/api/v1", tags=["热点话题"])

    # --- Direct /api/upload endpoint ---
    @app.post("/api/upload", tags=["files"], summary="Upload a file (Directly on App)")
    async def upload_file_main_app(file: UploadFile = FastApiFile(...)):
        logger.info(f"### backend_main.py: Received request at @app.post('/api/upload'), filename: '{file.filename}'")
        try:
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in ALLOWED_EXTENSIONS_MAIN:
                logger.warning(f"File upload rejected: Invalid file extension '{file_ext}' for file '{file.filename}'")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file type. Allowed types are: {', '.join(ALLOWED_EXTENSIONS_MAIN)}"
                )

            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = UPLOAD_DIR / unique_filename
            safe_file_path_repr = repr(str(file_path))
            logger.info(f"Attempting to save uploaded file '{file.filename}' as '{unique_filename}' to {safe_file_path_repr}")

            actual_size = 0
            try:
                with open(file_path, "wb") as buffer:
                    while content := await file.read(1024 * 1024):
                        actual_size += len(content)
                        if actual_size > MAX_FILE_SIZE:
                            buffer.close()
                            file_path.unlink()
                            logger.warning(f"File upload failed: File '{unique_filename}' exceeds size limit ({actual_size} > {MAX_FILE_SIZE})")
                            raise HTTPException(
                                status_code=413,
                                detail=f"File size exceeds the limit of {MAX_FILE_SIZE // (1024 * 1024)}MB."
                            )
                        buffer.write(content)
                if file_path.exists() and file_path.stat().st_size > MAX_FILE_SIZE:
                     file_path.unlink()
                     logger.warning(f"File upload failed (post-save check): File '{unique_filename}' exceeds size limit")
                     raise HTTPException(status_code=413, detail=f"File size exceeded limit post-save.")
            except HTTPException as http_exc:
                raise http_exc
            except Exception as e:
                logger.error(f"Failed to save uploaded file '{unique_filename}': {e}")
                if file_path.exists():
                    try: file_path.unlink()
                    except OSError: pass
                raise HTTPException(status_code=500, detail=f"Could not save file: {e}")

            logger.info(f"File '{file.filename}' uploaded successfully as '{unique_filename}'")
            return JSONResponse(
                content={
                    "status": "success",
                    "file_path": unique_filename,
                    "original_filename": file.filename
                },
                status_code=200
            )
        except HTTPException as http_exc:
            raise http_exc
        except Exception as e:
            logger.error(f"Unexpected error during file upload in main app: {e}")
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred during file upload: {str(e)}")

    # --- Global Exception Handler ---
    @app.exception_handler(Exception)
    async def 全局异常处理器(请求: Request, 异常: Exception):
        logger.error(f"全局异常处理器捕获到: {str(异常)}")
        return JSONResponse(
                status_code=500,
            content={"detail": "服务器内部错误"}
        )

    # --- 新增：配置 SPA 路由回退 ---
    # 1. 挂载静态文件目录 (除了 /api 之外的路径会尝试在这里查找)
    # 注意：确保这个路径相对于 backend_main.py 是正确的
    if FRONTEND_DIST_DIR.exists() and FRONTEND_DIST_DIR.is_dir():
        logger.info(f"Mounting static files from: {FRONTEND_DIST_DIR}")
        app.mount("/", StaticFiles(directory=FRONTEND_DIST_DIR, html=True), name="static")
    else:
        logger.warning(f"Frontend dist directory not found or not a directory: {FRONTEND_DIST_DIR}. SPA fallback may not work correctly.")

    # Define the startup function
    async def app_startup():
        await startup_event()  # Call original startup logic
        await init_db()      # Initialize the database
        initialize_handlers()  # Initialize the handler factory

    # Add startup/shutdown events
    logger.info("Adding startup and shutdown event handlers...")
    app.add_event_handler("startup", app_startup)
    app.add_event_handler("shutdown", shutdown_event)

    logger.info("FastAPI application instance created and configured.")
    return app

# --- Main entry point ---
if __name__ == "__main__":
    logger.info("Starting application via __main__ block...")
    app_instance = create_app()
    uvicorn.run(
        app_instance,
        host="0.0.0.0",
        port=8000,
        access_log=True,
        log_level="debug"
    )
