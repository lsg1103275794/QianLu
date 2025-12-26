"""
Startup and shutdown event handlers.
"""
import asyncio
# Import the manager instance directly
from src.core.tasks.manager import task_manager
from src.utils.logging import logger

# Import worker initialization function
try:
    # Import the function, not the instance directly
    from src.core.tasks.worker import initialize_worker, task_worker
    has_worker = True
except ImportError:
    logger.warning("任务worker模块未找到或初始化失败，异步任务处理将不可用")
    has_worker = False
    initialize_worker = None # Ensure it's None if import fails
    task_worker = None

async def startup_event():
    """Application startup event handler."""
    logger.info("Executing startup events...")
    try:
        # Initialize the Task Manager database table
        if task_manager:
            logger.info("Initializing TaskManager database...")
            await task_manager.initialize_db() # Ensure table exists
            logger.info("TaskManager database initialized.")

            # Initialize and start the Task Worker only AFTER DB is initialized
            if has_worker and initialize_worker:
                 logger.info("Initializing TaskWorker...")
                 worker_instance = initialize_worker() # Get the returned instance
                 if worker_instance:
                    logger.info("Starting TaskWorker...")
                    await worker_instance.start() # Start using the returned instance
                    logger.info("TaskWorker started.")
                 else:
                      logger.warning("TaskWorker instance could not be created by initialize_worker.")
            else:
                 logger.warning("TaskWorker module not available or initialization function missing.")
        else:
             logger.error("TaskManager instance is not available. Cannot initialize DB or start worker.")

        # 启动任务清理 (已注释掉，因为 SQLite TaskManager 暂未实现高效清理)
        # await task_manager.start_periodic_cleanup()
        # logger.info("Started periodic task cleanup")
        
    except Exception as e:
        logger.error(f"Error during startup sequence: {str(e)}", exc_info=True)
        # Depending on severity, might want to prevent app from fully starting
        raise
    logger.info("Startup events completed.")

async def shutdown_event():
    """Application shutdown event handler."""
    logger.info("Executing shutdown events...")
    try:
        # Stop the Task Worker first (if it exists and is running)
        if has_worker and task_worker and task_worker.is_running:
            logger.info("Stopping TaskWorker...")
            await task_worker.stop() # Stop using the global instance
            logger.info("TaskWorker stopped.")
        # REMOVED: No need to explicitly close TaskManager connection anymore
        # else:
        #     if task_manager:
        #          logger.info("Ensuring TaskManager database connection is closed...")
        #          await task_manager.close()
        #          logger.info("TaskManager database connection closed.")
        
        # 停止任务清理 (已注释掉)
        # await task_manager.stop_periodic_cleanup()
        # logger.info("Stopped periodic task cleanup")
    except Exception as e:
        logger.error(f"Error during shutdown sequence: {str(e)}", exc_info=True)
        raise
    logger.info("Shutdown events completed.") 