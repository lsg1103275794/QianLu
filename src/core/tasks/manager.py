"""
Task manager for handling asynchronous tasks using SQLite.
"""
import asyncio
import uuid
import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List
import aiosqlite
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler

from .models import Task, TaskStatus
from src.utils.logging import logger

# --- Database Configuration ---
# Ensure the data directory exists
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "tasks.db"

class TaskManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        logger.info(f"TaskManager initialized with SQLite backend at: {self.db_path}")

    async def initialize_db(self):
        """Create the tasks table if it doesn't exist."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Attempt to enable WAL mode for better concurrency
                try:
                    await db.execute("PRAGMA journal_mode=WAL;")
                    logger.info("SQLite journal_mode set to WAL for initialization.")
                except Exception as wal_e:
                    logger.warning(f"Failed to set SQLite journal_mode to WAL during initialization: {wal_e}.")

                async with db.cursor() as cursor:
                    await cursor.execute("""
                        CREATE TABLE IF NOT EXISTS tasks (
                            id TEXT PRIMARY KEY,
                            status TEXT NOT NULL,
                            progress REAL DEFAULT 0.0,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            metadata TEXT, -- Store as JSON string
                            result TEXT,   -- Store as JSON string
                            error TEXT
                        )
                    """)
                await db.commit()
                logger.info("'tasks' table checked/initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize 'tasks' table: {e}", exc_info=True)
            raise # Re-raise for startup process to know

    def _serialize_json(self, data: Optional[Dict[str, Any]]) -> Optional[str]:
        """Serialize dictionary to JSON string."""
        if data is None:
            return None
        try:
            # Ensure complex objects like datetimes are handled if necessary
            # (or ensure metadata/result don't contain them directly)
            return json.dumps(data)
        except TypeError as e:
            logger.error(f"Failed to serialize data to JSON: {e}. Data: {str(data)[:100]}...", exc_info=True)
            # Consider returning a specific error marker or raising
            return json.dumps({"error": "Serialization failed", "details": str(e)})

    def _deserialize_json(self, json_str: Optional[str]) -> Optional[Dict[str, Any]]:
        """Deserialize JSON string to dictionary."""
        if json_str is None:
            return None
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize JSON data: {e}. Data: {json_str[:100]}...", exc_info=True)
            # Consider returning a specific error marker or raising
            return {"error": "Deserialization failed", "details": str(e)}

    async def _row_to_task(self, row: aiosqlite.Row) -> Optional[Task]:
        """Convert a database row (dict-like) to a Task object."""
        if not row:
            return None
            
        task_id_from_row = "<ID not found in row>"
        try:
            row_dict = dict(row) # Convert Row object to a plain dict
            task_id_from_row = row_dict.get('id', task_id_from_row)
            
            status_val = row_dict['status']
            status = TaskStatus(status_val)
            
            created_at_str = row_dict['created_at']
            created_at = datetime.fromisoformat(created_at_str)
            
            updated_at_str = row_dict['updated_at']
            updated_at = datetime.fromisoformat(updated_at_str)
            
            metadata = self._deserialize_json(row_dict['metadata'])
            result = self._deserialize_json(row_dict['result'])
            
            task_obj = Task(
                 id=task_id_from_row,
                 status=status,
                 progress=row_dict['progress'],
                 created_at=created_at,
                 updated_at=updated_at,
                 metadata=metadata,
                 result=result,
                 error=row_dict['error']
            )
            return task_obj
            
        except (KeyError, ValueError, TypeError) as e:
             logger.error(f"[CONVERSION_ERROR] Failed during row conversion for task ID '{task_id_from_row}': {e}", exc_info=True)
             return None

    async def create_task(self, metadata: Optional[Dict[str, Any]] = None) -> Task:
        """Create a new task and store it in the SQLite database."""
        task_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        metadata_json = self._serialize_json(metadata)

        task = Task(
            id=task_id,
            status=TaskStatus.PENDING,
            progress=0.0,
            created_at=datetime.fromisoformat(now_iso), # Store as object in Task model
            updated_at=datetime.fromisoformat(now_iso),
            metadata=metadata # Store original dict in Task object
        )

        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row # Ensure row factory is set
                logger.info(f"[CREATE_TASK {task_id}] Attempting to insert into DB.")
                async with db.cursor() as cursor:
                    logger.debug(f"[CREATE_TASK {task_id}] Cursor obtained. Executing INSERT.")
                    await cursor.execute("""
                        INSERT INTO tasks (id, status, progress, created_at, updated_at, metadata)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (task_id, TaskStatus.PENDING.value, 0.0, now_iso, now_iso, metadata_json))
                    logger.debug(f"[CREATE_TASK {task_id}] INSERT executed. Attempting commit.")
                await db.commit()
                logger.info(f"[CREATE_TASK {task_id}] DB commit successful.")

            logger.info(f"Task {task_id} created record in SQLite.")
            return task # Return the Task object created in memory

        except Exception as e:
            logger.error(f"[CREATE_TASK {task_id}] Failed to store task in SQLite: {e}", exc_info=True)
            logger.error(f"[CREATE_TASK {task_id}] Task details at failure: ID={task_id}, Status={TaskStatus.PENDING.value}, Created={now_iso}, Metadata={metadata_json}")
            # Depending on requirements, might need to return None or a specific error Task
            raise # Re-raise the exception so the caller knows creation failed

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID from the SQLite database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                # Optional: Try WAL mode again, though might not be needed per-query
                # await db.execute("PRAGMA journal_mode=WAL;")

                async with db.cursor() as cursor:
                    logger.debug(f"[GET_TASK {task_id}] Executing SELECT query.")
                    await cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
                    row = await cursor.fetchone()
                    logger.debug(f"[GET_TASK {task_id}] Query executed. Row found: {row is not None}")

            if not row:
                logger.warning(f"[GET_TASK {task_id}] Task not found in database query result.")
                return None

            # Convert row to Task object (outside the DB connection context)
            task_object = await self._row_to_task(row) # Uses the helper method
            if not task_object:
                 logger.error(f"[GET_TASK {task_id}] Task found in DB, but failed row conversion.")
                 return None # Indicate conversion failure

            logger.info(f"[GET_TASK {task_id}] Successfully retrieved and converted task.")
            return task_object

        except Exception as e:
            logger.error(f"[GET_TASK {task_id}] Exception during execution: {e}", exc_info=True)
            return None # Return None on error

    async def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[float] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> Optional[Task]: # Return updated task or None on failure/not found
        """Update a task's status, progress, result, or error in SQLite."""
        updates = {}
        params_list = [] # Use list for ordered parameters

        now_iso = datetime.now(timezone.utc).isoformat()
        updates['updated_at'] = '?'
        params_list.append(now_iso)

        if status is not None:
            updates['status'] = '?'
            params_list.append(status.value)
        if progress is not None:
            updates['progress'] = '?'
            params_list.append(progress)
        if result is not None:
            updates['result'] = '?'
            params_list.append(self._serialize_json(result))
        if error is not None:
            updates['error'] = '?'
            params_list.append(error)

        if len(updates) <= 1: # Only updated_at is present
            logger.warning(f"[UPDATE_TASK {task_id}] No substantive updates provided.")
            # Return current state? Need to query again. For simplicity, return None now.
            # Or perhaps query and return the task state if needed by caller.
            return None # Indicate no update occurred or query current state

        set_clause = ", ".join(f"{key} = {value}" for key, value in updates.items())
        sql = f"UPDATE tasks SET {set_clause} WHERE id = ?"
        params_list.append(task_id) # Add task_id for WHERE clause

        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.cursor() as cursor:
                    logger.debug(f"[UPDATE_TASK {task_id}] Executing UPDATE with params: {params_list}")
                    await cursor.execute(sql, params_list)
                    rows_affected = cursor.rowcount
                await db.commit()
                logger.debug(f"[UPDATE_TASK {task_id}] Commit successful. Rows affected: {rows_affected}")

            if rows_affected > 0:
                logger.info(f"[UPDATE_TASK {task_id}] Task updated successfully in SQLite.")
                # Fetch the updated task state to return it
                return await self.get_task(task_id)
            else:
                logger.warning(f"[UPDATE_TASK {task_id}] UPDATE executed but no rows were affected (task ID likely not found).")
                return None

        except Exception as e:
            logger.error(f"[UPDATE_TASK {task_id}] Failed to update task: {e}", exc_info=True)
            return None # Indicate failure

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task by setting its status to CANCELLED."""
        logger.info(f"[CANCEL_TASK {task_id}] Attempting to cancel task.")
        # Use update_task for consistency
        updated_task = await self.update_task(task_id, status=TaskStatus.CANCELLED)
        if updated_task and updated_task.status == TaskStatus.CANCELLED:
             logger.info(f"[CANCEL_TASK {task_id}] Task successfully marked as CANCELLED.")
             return True
        else:
             logger.warning(f"[CANCEL_TASK {task_id}] Failed to cancel task (not found or update failed).")
             return False

    async def get_pending_tasks(self, limit: int = 10) -> List[Task]:
        """Get a list of pending tasks from SQLite."""
        tasks = []
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.cursor() as cursor:
                    # 降低查询日志级别，仅在DEBUG级别和开发模式下记录
                    if os.environ.get("DEV_MODE") == "1" and logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"[WORKER_FETCH] Querying for PENDING tasks (limit {limit}).")
                    await cursor.execute(
                        "SELECT * FROM tasks WHERE status = ? ORDER BY created_at ASC LIMIT ?",
                        (TaskStatus.PENDING.value, limit)
                    )
                    rows = await cursor.fetchall()
                    # 只有在找到任务时才记录信息日志
                    if len(rows) > 0:
                        logger.info(f"[WORKER_FETCH] Found {len(rows)} PENDING tasks in query result.")
                    # 完全删除"没有任务"的DEBUG日志，减少干扰

            # Convert rows outside the connection context
            for row in rows:
                task_obj = await self._row_to_task(row)
                if task_obj:
                    tasks.append(task_obj)
                else:
                    # Log conversion error for specific row if needed, using row['id']
                    task_id_in_row = dict(row).get('id', '<unknown_id>')
                    logger.error(f"[WORKER_FETCH] Failed to convert row to task object for ID: {task_id_in_row}")

            # 降低返回日志级别，只在有任务时记录INFO级别
            if len(tasks) > 0:
                logger.info(f"[WORKER_FETCH] Returning {len(tasks)} successfully converted PENDING tasks.")
            # 删除"无任务处理"的DEBUG日志，减少干扰
            
            return tasks

        except Exception as e:
            logger.error(f"[WORKER_FETCH] Failed to get pending tasks: {e}", exc_info=True)
            return [] # Return empty list on error

# --- Global TaskManager instance ---
# Initialize the global instance
task_manager = TaskManager()
# Note: initialize_db() should be called explicitly during application startup 