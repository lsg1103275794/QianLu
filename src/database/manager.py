"""""
Database management using SQLAlchemy for storing result metadata.
"""

import os
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Optional

from sqlalchemy import create_engine, Column, Integer, String, DateTime, select, MetaData, Table, Text, UniqueConstraint, Index
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy.sql import func

from src.utils.logging import logger

# --- Configuration ---
DATABASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(DATABASE_DIR, 'glyphmind_data.db')}"

os.makedirs(DATABASE_DIR, exist_ok=True)

logger.info(f"Database directory: {DATABASE_DIR}")
logger.info(f"Database URL: {DATABASE_URL}")

# --- SQLAlchemy Setup (Async) ---
engine = create_async_engine(DATABASE_URL, echo=False) # Set echo=True for SQL query debugging

async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

Base = declarative_base()

# --- Database Model Definition ---

class Result(Base):
    __tablename__ = 'results'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Unique ID for the result, could be hash of file path or UUID
    result_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String) # User-defined name, initially might be null or derived
    type: Mapped[str] = mapped_column(String, index=True, nullable=False) # e.g., 'text_analysis', 'literature_analysis', 'style_transfer', 'excel_analysis'
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    source_info: Mapped[Optional[str]] = mapped_column(Text) # e.g., original filename, text snippet
    model_info: Mapped[Optional[str]] = mapped_column(String) # e.g., provider + model name
    file_path: Mapped[str] = mapped_column(String, nullable=False) # Relative or absolute path to the JSON result file
    # Consider a separate table for tags if complex tagging is needed
    tags: Mapped[Optional[str]] = mapped_column(String) # Simple comma-separated tags for now

    # Add unique constraint and index explicitly if needed beyond single column flags
    __table_args__ = (
        Index('ix_results_timestamp', 'timestamp'), # Index timestamp for sorting
    )

    def __repr__(self):
        return f"<Result(id={self.id}, result_id='{self.result_id}', name='{self.name}', type='{self.type}', timestamp={self.timestamp})>"

# --- Database Initialization ---

async def init_db():
    """Initializes the database and creates tables if they don't exist."""
    async with engine.begin() as conn:
        logger.info("Initializing database and creating tables if they don't exist...")
        # Base.metadata.create_all will create tables based on models inheriting from Base
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialization complete.")

# --- Dependency for FastAPI Routes ---

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

# --- Basic CRUD Operations (Example) ---

async def add_result_record(db: AsyncSession, **kwargs):
    """Adds a new result record to the database."""
    # Ensure required fields are present (example)
    required_fields = ['result_id', 'type', 'file_path']
    for field in required_fields:
        if field not in kwargs or not kwargs[field]:
            raise ValueError(f"Missing required field for result record: {field}")
    
    # Add timestamp if not provided
    if 'timestamp' not in kwargs:
        kwargs['timestamp'] = datetime.now()
        
    new_result = Result(**kwargs)
    try:
        db.add(new_result)
        await db.commit()
        await db.refresh(new_result)
        logger.info(f"Added result record: {new_result.result_id} ({new_result.type})")
        return new_result
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to add result record for {kwargs.get('result_id')}: {e}")
        raise

async def list_results(db: AsyncSession, limit: int = 100, offset: int = 0) -> List[Result]:
    """Lists result records from the database, ordered by timestamp descending."""
    try:
        stmt = select(Result).order_by(Result.timestamp.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        results = result.scalars().all()
        logger.debug(f"Fetched {len(results)} result records (limit={limit}, offset={offset}).")
        return results
    except Exception as e:
        logger.error(f"Failed to list result records: {e}")
        raise

# --- Add other CRUD operations as needed (get_result_by_id, update_result, delete_result) ---

async def get_result_by_result_id(db: AsyncSession, result_id: str) -> Optional[Result]:
    """Retrieves a specific result record by its unique result_id."""
    try:
        stmt = select(Result).where(Result.result_id == result_id)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        if record:
             logger.debug(f"Fetched result record by result_id: {result_id}")
        else:
             logger.debug(f"Result record with result_id {result_id} not found.")
        return record
    except Exception as e:
        logger.error(f"Failed to get result record by result_id {result_id}: {e}")
        raise # Re-raise

async def delete_result_record(db: AsyncSession, result_id: str) -> bool:
    """Deletes a specific result record by its unique result_id. Returns True if deleted, False otherwise."""
    try:
        stmt = select(Result).where(Result.result_id == result_id)
        result = await db.execute(stmt)
        record_to_delete = result.scalar_one_or_none()

        if record_to_delete:
            await db.delete(record_to_delete)
            await db.commit()
            logger.info(f"Deleted result record with result_id: {result_id}")
            return True
        else:
            logger.warning(f"Result record with result_id {result_id} not found for deletion.")
            return False
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete result record with result_id {result_id}: {e}")
        raise # Re-raise

async def update_result_name(db: AsyncSession, result_id: str, new_name: str) -> bool:
    """Updates the name of a specific result record."""
    if not result_id or not new_name:
        logger.warning("update_result_name called with empty result_id or new_name.")
        return False
        
    try:
        stmt = select(Result).where(Result.result_id == result_id)
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()
        
        if record:
            record.name = new_name
            record.updated_at = datetime.now(timezone.utc) # Also update timestamp
            await db.commit()
            logger.info(f"Updated name for result {result_id} to '{new_name}'")
            return True
        else:
            logger.warning(f"Result with ID {result_id} not found for renaming.")
            return False
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update name for result {result_id}: {e}")
        raise # Re-raise to let the API layer handle it 