"""
Task-related API routes.
"""
from fastapi import APIRouter, HTTPException
from src.core.tasks.models import Task, TaskStatus
from src.core.tasks.manager import task_manager
from src.utils.logging import logger

# 修改路由前缀以确保它在多个路径下可访问
router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.get("/{task_id}", response_model=Task, summary="获取任务状态")
async def get_task_status(task_id: str):
    """Get task status by ID."""
    # Use print for absolute certainty
    print(f"--- PRINT DEBUG: Entering get_task_status for task_id: {task_id} ---") 
    logger.info(f"[API GET ENTRY] Received request for task_id: {task_id}")

    clean_task_id = task_id
    try:
        # 处理可能带有时间戳的任务ID (加 try-except 以防万一)
        clean_task_id = task_id.split('_')[0]
        if clean_task_id != task_id:
            logger.info(f"[API GET] Cleaned task ID: {task_id} -> {clean_task_id}")
    except Exception as e_clean:
        logger.error(f"[API GET] Error cleaning task ID '{task_id}': {e_clean}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid task ID format")

    logger.info(f"[API GET] Attempting task_manager.get_task for clean_id: {clean_task_id}")
    task = None
    task_result_type = "Not Called" # 初始化
    try:
        task = await task_manager.get_task(clean_task_id)
        task_result_type = type(task) # 获取实际类型
        logger.info(f"[API GET] task_manager.get_task call completed. Result type: {task_result_type}")
    except Exception as e_get:
        logger.error(f"[API GET] Exception during task_manager.get_task call for {clean_task_id}: {e_get}", exc_info=True)
        task_result_type = "Exception Occurred" # 标记异常

    # 无论如何都记录 get_task 的结果摘要
    logger.info(f"[API GET] Result summary after get_task: task is None = {task is None}, type = {task_result_type}")

    if not task:
        logger.warning(f"[API GET] Task object is None for ID: {clean_task_id}. Raising 404.")
        # 记录日志以便调试 (这条似乎重复了，但保留以防万一)
        logger.warning(f"未找到任务ID(中文): {clean_task_id}")
        raise HTTPException(status_code=404, detail="Task not found")

    logger.info(f"[API GET] Task {clean_task_id} found. Status: {task.status}. Returning task.")
    return task

@router.get("/{task_id}/status", response_model=Task, summary="获取任务状态(兼容路径)")
async def get_task_status_compat(task_id: str):
    """兼容路径 - 获取任务状态"""
    return await get_task_status(task_id)

@router.post("/{task_id}/cancel", summary="取消任务")
async def cancel_task(task_id: str):
    """Cancel a task."""
    logger.info(f"尝试取消任务: {task_id}")
    
    # 处理可能带有时间戳的任务ID
    clean_task_id = task_id.split('_')[0]  # 去除时间戳部分
    if clean_task_id != task_id:
        logger.info(f"处理带时间戳的任务ID: {task_id} -> {clean_task_id}")
    
    success = await task_manager.cancel_task(clean_task_id)
    if not success:
        logger.warning(f"无法取消任务 {clean_task_id}: 任务不存在或无法取消")
        raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")
    logger.info(f"成功取消任务: {clean_task_id}")
    return {"status": "success"} 