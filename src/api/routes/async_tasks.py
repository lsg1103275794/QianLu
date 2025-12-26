"""
异步任务API路由
"""
from fastapi import APIRouter, HTTPException
from src.core.tasks.models import Task, TaskStatus
from src.core.tasks.manager import task_manager
from src.utils.logging import logger

# 创建一个专门的异步任务路由
router = APIRouter(prefix="/api/async/tasks", tags=["async_tasks"])

@router.get("/{task_id}", response_model=Task, summary="通过异步API获取任务状态")
async def get_task_status(task_id: str):
    """获取异步任务状态
    
    参数:
    - task_id: 任务ID
    
    返回:
    - Task: 任务对象，包含状态、结果等信息
    """
    logger.info(f"正在通过异步API查询任务状态: {task_id}")
    
    # 处理可能带有时间戳的任务ID
    clean_task_id = task_id.split('_')[0]  # 去除时间戳部分
    if clean_task_id != task_id:
        logger.info(f"处理带时间戳的任务ID: {task_id} -> {clean_task_id}")
    
    task = task_manager.get_task(clean_task_id)
    if not task:
        logger.warning(f"未找到任务ID: {clean_task_id} (异步API)")
        raise HTTPException(status_code=404, detail="Task not found")
    logger.info(f"异步任务 {clean_task_id} 状态: {task.status}")
    return task

@router.get("/{task_id}/status", response_model=Task, summary="通过异步API获取任务状态(兼容)")
async def get_task_status_compat(task_id: str):
    """兼容路径 - 获取异步任务状态"""
    return await get_task_status(task_id)

@router.post("/{task_id}/cancel", summary="通过异步API取消任务")
async def cancel_task(task_id: str):
    """取消异步任务
    
    参数:
    - task_id: 任务ID
    
    返回:
    - 成功或失败信息
    """
    logger.info(f"尝试通过异步API取消任务: {task_id}")
    
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