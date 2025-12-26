import os
import json
import time
import hashlib
from typing import Dict, Any, Optional, Tuple, List
import logging
from pathlib import Path
import threading
import pickle
from datetime import datetime, timezone
# --- Database Imports ---
from sqlalchemy.ext.asyncio import AsyncSession # Import AsyncSession
from src.database.manager import add_result_record # Import the function to add records
from sqlalchemy import select
from src.database.manager import Result # Import the Result model
# -----------------------

logger = logging.getLogger(__name__)

class TextProcessingCache:
    """
    用于缓存 LLM 文本处理结果的缓存系统，支持内存缓存和磁盘持久化。
    
    特性:
    - 内存 LRU 缓存，限制最大条目数
    - 磁盘持久化，在应用重启后恢复
    - 线程安全操作
    - 缓存键基于输入参数的哈希
    - 支持缓存有效期
    """
    
    def __init__(self, maxsize: int = 100, cache_dir: Optional[str] = None, ttl: int = 86400):
        """
        初始化缓存系统。
        
        参数:
            maxsize: 内存缓存的最大条目数
            cache_dir: 磁盘缓存目录，如果为 None，则不使用磁盘缓存
            ttl: 缓存条目的生存时间（秒），默认 24 小时
        """
        self._cache: Dict[str, Dict[str, Any]] = {}  # 内存缓存
        self._keys: List[str] = []  # LRU 列表
        self.maxsize = max(10, maxsize)  # 确保最小容量
        self.ttl = ttl  # 缓存过期时间
        self._lock = threading.RLock()  # 递归锁，允许同一线程多次获取
        
        # 设置磁盘缓存
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # 默认在项目根目录的 .cache 文件夹
            self.cache_dir = Path(__file__).resolve().parent.parent.parent / ".cache" / "text_processing"
        
        # 确保缓存目录存在
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 尝试从磁盘加载缓存
        self._load_from_disk()
        
        logger.info(f"TextProcessingCache 初始化：最大容量 {self.maxsize}，目录 {self.cache_dir}")
    
    def _create_key(self, *args) -> str:
        """
        基于输入参数创建缓存键。
        使用 SHA-256 哈希来确保键的唯一性和固定长度。
        """
        # 将所有参数序列化为 JSON 字符串
        serialized = json.dumps(args, ensure_ascii=False, sort_keys=True)
        # 计算哈希值
        key = hashlib.sha256(serialized.encode('utf-8')).hexdigest()
        return key
    
    def get(self, *args) -> Optional[Dict[str, Any]]:
        """
        从缓存中获取项。
        如果找到并且未过期，则返回缓存项并更新 LRU 顺序。
        如果未找到或已过期，则返回 None。
        """
        key = self._create_key(*args)
        
        with self._lock:
            # 首先检查内存缓存
            if key in self._cache:
                item = self._cache[key]
                current_time = time.time()
                
                # 检查是否过期
                if "timestamp" in item and current_time - item["timestamp"] > self.ttl:
                    logger.debug(f"缓存项 {key[:8]} 已过期")
                    self._remove_item(key)
                    return None
                
                # 更新 LRU 顺序
                self._keys.remove(key)
                self._keys.append(key)
                
                logger.debug(f"内存缓存命中：{key[:8]}")
                return item
            
            # 检查磁盘缓存
            disk_item = self._load_from_disk_by_key(key)
            if disk_item:
                # 添加到内存缓存
                self._add_to_memory_cache(key, disk_item)
                logger.debug(f"磁盘缓存命中：{key[:8]}")
                return disk_item
        
        logger.debug(f"缓存未命中：{key[:8]}")
        return None
    
    def set(self, value: Dict[str, Any], *args) -> None:
        """
        将项添加到缓存。
        如果达到最大容量，则移除最近最少使用的项。
        """
        if not isinstance(value, dict):
            logger.warning(f"缓存值必须是字典，而不是 {type(value)}")
            return
        
        key = self._create_key(*args)
        
        # 添加时间戳
        value["timestamp"] = time.time()
        
        with self._lock:
            # 添加到内存缓存
            self._add_to_memory_cache(key, value)
            
            # 保存到磁盘
            self._save_to_disk_by_key(key, value)
        
        logger.debug(f"已添加到缓存：{key[:8]}")
    
    def _add_to_memory_cache(self, key: str, value: Dict[str, Any]) -> None:
        """添加项到内存缓存，管理 LRU 顺序"""
        # 如果键已存在，先移除它
        if key in self._cache:
            self._keys.remove(key)
        # 如果达到最大容量，移除最老的项
        elif len(self._cache) >= self.maxsize:
            oldest_key = self._keys.pop(0)
            del self._cache[oldest_key]
            logger.debug(f"LRU 缓存已满，移除最老项：{oldest_key[:8]}")
        
        # 添加新项
        self._cache[key] = value
        self._keys.append(key)
    
    def _remove_item(self, key: str) -> None:
        """从内存和磁盘缓存中移除项"""
        # 从内存缓存移除
        if key in self._cache:
            del self._cache[key]
        if key in self._keys:
            self._keys.remove(key)
        
        # 从磁盘缓存移除
        disk_path = self.cache_dir / f"{key}.json"
        if disk_path.exists():
            try:
                os.remove(disk_path)
                logger.debug(f"从磁盘缓存移除：{key[:8]}")
            except Exception as e:
                logger.warning(f"从磁盘移除缓存 {key[:8]} 失败: {e}")
    
    def _get_disk_cache_path(self, key: str) -> Path:
        """获取磁盘缓存文件路径"""
        return self.cache_dir / f"{key}.json"
    
    def _save_to_disk_by_key(self, key: str, value: Dict[str, Any]) -> bool:
        """将单个缓存项保存到磁盘"""
        try:
            cache_path = self._get_disk_cache_path(key)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(value, f, ensure_ascii=False)
            return True
        except Exception as e:
            logger.warning(f"保存缓存项 {key[:8]} 到磁盘失败: {e}")
            return False
    
    def _load_from_disk_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """从磁盘加载单个缓存项"""
        cache_path = self._get_disk_cache_path(key)
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                item = json.load(f)
            
            # --- Handle different timestamp formats --- 
            timestamp_value = item.get("timestamp")
            timestamp_float: Optional[float] = None
            if isinstance(timestamp_value, (int, float)):
                timestamp_float = float(timestamp_value)
            elif isinstance(timestamp_value, str):
                try:
                    # Attempt to parse ISO format string
                    dt_obj = datetime.fromisoformat(timestamp_value.replace('Z', '+00:00')) # Handle Z timezone
                    timestamp_float = dt_obj.timestamp()
                except ValueError:
                    logger.warning(f"Invalid timestamp string format in cache file {key[:8]}: {timestamp_value}")
            else:
                 logger.warning(f"Missing or invalid timestamp type in cache file {key[:8]}: {type(timestamp_value)}")
            # -----------------------------------------

            # 检查是否过期 (use timestamp_float)
            current_time = time.time()
            if timestamp_float is not None and current_time - timestamp_float > self.ttl:
                logger.debug(f"磁盘缓存项 {key[:8]} 已过期 (timestamp: {timestamp_float})")
                try:
                    os.remove(cache_path)
                except Exception:
                    pass
                return None
            elif timestamp_float is None:
                 # Treat items with invalid/missing timestamp as potentially expired or handle differently?
                 # For now, let's log and return None to avoid using potentially stale data.
                 logger.warning(f"Treating cache item {key[:8]} as invalid due to missing/unparseable timestamp.")
                 # Optionally remove the file here too?
                 # try: os.remove(cache_path) except Exception: pass
                 return None 
            
            return item
        except Exception as e:
            logger.warning(f"从磁盘加载缓存项 {key[:8]} 失败: {e}")
            return None
    
    def _load_from_disk(self) -> None:
        """从磁盘加载所有缓存项"""
        try:
            json_files = list(self.cache_dir.glob("*.json"))
            if not json_files:
                logger.debug("磁盘缓存为空")
                return
            
            # 只加载有限数量的文件，避免占用太多内存
            # 优先加载最新的文件（基于修改时间）
            json_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            files_to_load = json_files[:self.maxsize]
            
            for file_path in files_to_load:
                try:
                    key = file_path.stem  # 不含扩展名的文件名就是键
                    with open(file_path, 'r', encoding='utf-8') as f:
                        item = json.load(f)
                    
                    # --- Handle different timestamp formats (same logic as above) --- 
                    timestamp_value = item.get("timestamp")
                    timestamp_float: Optional[float] = None
                    if isinstance(timestamp_value, (int, float)):
                        timestamp_float = float(timestamp_value)
                    elif isinstance(timestamp_value, str):
                        try:
                            dt_obj = datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
                            timestamp_float = dt_obj.timestamp()
                        except ValueError:
                            logger.warning(f"Invalid timestamp string format in cache file {key[:8]}: {timestamp_value}")
                    else:
                         logger.warning(f"Missing or invalid timestamp type in cache file {key[:8]}: {type(timestamp_value)}")
                    # ------------------------------------------------------------

                    # 检查是否过期
                    current_time = time.time()
                    if timestamp_float is not None and current_time - timestamp_float > self.ttl:
                        logger.debug(f"Removing expired cache file from disk: {file_path.name}")
                        os.remove(file_path)
                        continue
                    elif timestamp_float is None:
                        logger.warning(f"Skipping cache file {file_path.name} due to missing/invalid timestamp.")
                        # Optionally remove invalid file?
                        # os.remove(file_path)
                        continue
                    
                    # 添加到内存缓存
                    self._add_to_memory_cache(key, item)
                except Exception as e:
                    logger.warning(f"加载缓存文件 {file_path.name} 失败: {e}")
            
            logger.info(f"从磁盘加载了 {len(self._cache)} 个缓存项")
        except Exception as e:
            logger.warning(f"从磁盘加载缓存失败: {e}")
    
    def clear(self) -> None:
        """清空缓存（内存和磁盘）"""
        with self._lock:
            # 清空内存缓存
            self._cache.clear()
            self._keys.clear()
            
            # 清空磁盘缓存
            try:
                for file_path in self.cache_dir.glob("*.json"):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
                logger.info("缓存已清空")
            except Exception as e:
                logger.warning(f"清空磁盘缓存失败: {e}")
    
    def clear_expired(self) -> int:
        """
        清除过期的缓存项。
        返回清除的项数。
        """
        with self._lock:
            count = 0
            current_time = time.time()
            
            # 检查内存缓存
            expired_keys = []
            for key, item in self._cache.items():
                if "timestamp" in item and current_time - item["timestamp"] > self.ttl:
                    expired_keys.append(key)
            
            # 从内存中移除过期项
            for key in expired_keys:
                if key in self._cache:
                    del self._cache[key]
                if key in self._keys:
                    self._keys.remove(key)
                count += 1
            
            # 检查磁盘缓存
            try:
                for file_path in self.cache_dir.glob("*.json"):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            item = json.load(f)
                        
                        if "timestamp" in item and current_time - item["timestamp"] > self.ttl:
                            os.remove(file_path)
                            count += 1
                    except Exception:
                        # 如果读取失败，假设文件已损坏，移除它
                        try:
                            os.remove(file_path)
                            count += 1
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"清理磁盘缓存失败: {e}")
            
            logger.info(f"已清除 {count} 个过期缓存项")
            return count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息。
        返回一个包含当前状态的字典。
        """
        with self._lock:
            # 计算磁盘缓存大小和项数
            disk_size = 0
            disk_count = 0
            try:
                for file_path in self.cache_dir.glob("*.json"):
                    try:
                        disk_size += file_path.stat().st_size
                        disk_count += 1
                    except Exception:
                        pass
            except Exception:
                pass
            
            # 返回统计信息
            return {
                "memory_items": len(self._cache),
                "memory_capacity": self.maxsize,
                "memory_usage": len(self._cache) / self.maxsize if self.maxsize > 0 else 0,
                "disk_items": disk_count,
                "disk_size_bytes": disk_size,
                "disk_size_mb": disk_size / (1024 * 1024) if disk_size > 0 else 0,
                "ttl_seconds": self.ttl,
                "cache_dir": str(self.cache_dir)
            }

cache = TextProcessingCache()

# 定义不同模块的缓存目录
PROJECT_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CACHE_BASE_DIR = PROJECT_ROOT_DIR / ".cache"
OUTPUT_DATASETS_DIR = PROJECT_ROOT_DIR / "data" / "output" / "datasets"

# 确保目录存在
CACHE_BASE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DATASETS_DIR.mkdir(parents=True, exist_ok=True)

# 创建不同模块的缓存实例，并为 literature 指定特殊目录
text_analysis_cache = TextProcessingCache(cache_dir=str(CACHE_BASE_DIR / "text_analysis"))
literature_analysis_cache = TextProcessingCache(cache_dir=str(OUTPUT_DATASETS_DIR))
style_transfer_cache = TextProcessingCache(cache_dir=str(CACHE_BASE_DIR / "style_transfer"))
analysis_results_index = TextProcessingCache(cache_dir=str(CACHE_BASE_DIR / "index"), maxsize=1000)

def generate_result_id(module_type, result_data):
    """Generate a unique ID based on the provided result data."""
    logger.debug(f"Generating result ID for {module_type} with data keys: {list(result_data.keys())}")
    
    # Create a base string for hashing
    timestamp = result_data.get("timestamp", datetime.now().isoformat())
    base_string = f"{module_type}_{timestamp}"
    
    # Add text content if available (first 100 chars)
    if "text" in result_data and result_data["text"] is not None:
        try:
            text_slice = str(result_data["text"])[:100]
            base_string += "_" + text_slice
        except (TypeError, ValueError) as e:
            logger.error(f"Error processing text field: {e}")
    
    # Add result if available (first 100 chars)
    try:
        if "result" in result_data and result_data["result"] is not None:
            result_str = str(result_data["result"])
            result_slice = result_str[:100]
            base_string += "_" + result_slice
    except (KeyError, TypeError, IndexError, ValueError) as e:
        logger.error(f"Error processing result field: {e}")
    
    # Add content if available (first 100 chars)
    if "content" in result_data and result_data["content"] is not None:
        try:
            content_slice = str(result_data["content"])[:100]
            base_string += "_" + content_slice
        except (TypeError, ValueError) as e:
            logger.error(f"Error processing content field: {e}")
    
    # Calculate hash as ID
    result_id = hashlib.sha256(base_string.encode('utf-8')).hexdigest()
    return result_id

# Modify function signature to accept db session
async def save_analysis_result(module_type, result_data, db: AsyncSession):
    """
    保存分析结果到指定的模块缓存目录，更新索引，并记录元数据到数据库。

    Args:
        module_type: 模块类型 ('text', 'literature', 'style', etc.)
        result_data: 要保存的结果字典
        db: SQLAlchemy AsyncSession for database operations.

    Returns:
        生成的 result_id 或 None (如果保存失败)
    """
    if not module_type or not isinstance(result_data, dict):
        logger.error("保存分析结果失败：模块类型或结果数据无效")
        return None
    if not db:
        logger.error("保存分析结果失败：数据库会话无效")
        return None

    # Add/update timestamp (use timezone aware)
    result_data["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Generate unique ID
    result_id = generate_result_id(module_type, result_data)
    if not result_id:
        logger.error("生成 result_id 失败")
        return None

    # Get cache directory and file path
    cache_dir = get_cache_dir(module_type)
    if not cache_dir:
        logger.error(f"获取模块 '{module_type}' 的缓存目录失败")
        return None
    cache_dir.mkdir(parents=True, exist_ok=True)
    file_path = cache_dir / f"{result_id}.json"

    file_saved_successfully = False
    try:
        # Save JSON file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        file_saved_successfully = True
        logger.info(f"成功保存 {module_type} 分析结果文件: {file_path.name}")

        # --- Add record to database --- 
        try:
            # Extract metadata from result_data
            timestamp_dt = datetime.fromisoformat(result_data["timestamp"]) # Use the parsed datetime object
            
            # --- Generate default name if not provided --- 
            provided_name = result_data.get('name')
            if not provided_name or not str(provided_name).strip():
                # Use timestamp from the data for consistency
                timestamp_str = timestamp_dt.strftime('%Y%m%d_%H%M%S') 
                default_name = f"{module_type.capitalize()} - {timestamp_str}"
                logger.debug(f"No name provided for result {result_id}, generating default: {default_name}")
                record_name = default_name
            else:
                record_name = str(provided_name).strip()
            # --------------------------------------------
            
            metadata = {
                'result_id': result_id,
                'type': module_type,
                'file_path': str(file_path.relative_to(Path(__file__).resolve().parent.parent.parent)), # Store relative path
                'timestamp': timestamp_dt,
                'name': record_name, # Use the determined name
                # Prioritize source_info from payload, then fall back
                'source_info': result_data.get('source_info') or result_data.get('text_summary') or result_data.get('original_filename'), 
                'model_info': f"{result_data.get('provider', 'N/A')}/{result_data.get('model', 'N/A')}" if result_data.get('provider') else None,
                'tags': None # Placeholder for tags
            }
            await add_result_record(db, **metadata)
        except Exception as db_err:
            logger.exception(f"数据库记录失败 for result {result_id}: {db_err}. JSON 文件已保存.")
            # Decide if we should re-raise or just log. Logging for now.
        # ------------------------------

        return result_id

    except Exception as e:
        logger.exception(f"保存 {module_type} 分析结果到文件 {file_path} 失败: {e}")
        # If file saving failed, don't try to add DB record (already handled by structure)
        # If DB saving failed after file save, the file still exists.
        # Consider cleanup logic if needed.
        return None

# Refactor get_analysis_result to use the database
async def get_analysis_result(result_id: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
    """
    Retrieves analysis result content by reading the JSON file specified in the database.

    Args:
        result_id: The unique ID of the result.
        db: SQLAlchemy AsyncSession for database access.

    Returns:
        The parsed JSON content of the result file, or None if not found or error occurs.
    """
    if not result_id or not db:
        logger.error("get_analysis_result called with invalid result_id or db session.")
        return None

    try:
        # Query the database for the result record
        stmt = select(Result).where(Result.result_id == result_id)
        db_result = await db.execute(stmt)
        record = db_result.scalar_one_or_none()

        if not record:
            logger.warning(f"Result record with ID '{result_id}' not found in database.")
            return None

        if not record.file_path:
            logger.error(f"Result record {result_id} found, but file_path is missing.")
            return None

        # Construct the absolute file path
        # Assuming record.file_path is relative to PROJECT_ROOT_DIR defined earlier
        absolute_file_path = PROJECT_ROOT_DIR / record.file_path
        logger.info(f"Attempting to read result file: {absolute_file_path}")

        if not absolute_file_path.is_file():
            logger.error(f"Result file not found at path: {absolute_file_path}")
            return None

        # Read and parse the JSON file
        try:
            with open(absolute_file_path, 'r', encoding='utf-8') as f:
                result_content = json.load(f)
            logger.info(f"Successfully retrieved and parsed result content for {result_id}.")
            return result_content
        except json.JSONDecodeError as json_err:
            logger.error(f"Failed to decode JSON from result file {absolute_file_path}: {json_err}")
            return None
        except Exception as read_err:
            logger.error(f"Failed to read result file {absolute_file_path}: {read_err}", exc_info=True)
            return None

    except Exception as db_err:
        logger.error(f"Database error while retrieving result {result_id}: {db_err}", exc_info=True)
        return None

# --- Define get_cache_dir Function --- 
def get_cache_dir(module_type: str) -> Optional[Path]:
    """Returns the specific cache directory path for a given module type."""
    if module_type == 'text':
        return CACHE_BASE_DIR / "text_analysis"
    elif module_type == 'literature':
        # Special case for literature, using output datasets dir
        return OUTPUT_DATASETS_DIR 
    elif module_type == 'style':
        return CACHE_BASE_DIR / "style_transfer"
    # Add other module types here if needed
    # elif module_type == 'excel':
    #     return CACHE_BASE_DIR / "excel_analysis"
    else:
        logger.warning(f"Unknown module type '{module_type}' requested for cache directory.")
        # Fallback to a general cache dir or return None
        # Returning None to indicate failure might be safer
        return None 
# ------------------------------------

if __name__ == '__main__':
    print("--- 测试缓存 ---")
    test_cache = TextProcessingCache(maxsize=3)

    key1_args = ("param1", "param2")
    key1_kwargs = {"opt": 1}
    key2_args = ("param1", "param3")
    key3_args = ("param1", "param2")
    key3_kwargs = {"opt": 2}
    key4_args = ("param1", "param2")
    key4_kwargs = {"opt": 1}
    key_complex_args = (["a", "b"], {"c": 3})

    print("设置缓存值:")
    test_cache.set("value1", *key1_args, **key1_kwargs)
    print(f"Cache info: {test_cache.get_stats()}")
    test_cache.set("value2", *key2_args)
    print(f"Cache info: {test_cache.get_stats()}")
    test_cache.set("value3", *key3_args, **key3_kwargs)
    print(f"Cache info: {test_cache.get_stats()}")

    print("\n获取缓存值:")
    print(f"Get key1: {test_cache.get(*key1_args, **key1_kwargs)}")
    print(f"Get key2: {test_cache.get(*key2_args)}")
    print(f"Get key3: {test_cache.get(*key3_args, **key3_kwargs)}")

    print("\n添加第四个值，应该会挤掉最早的 value2 (key2):")
    test_cache.set("value4", "another_param")
    print(f"Cache info: {test_cache.get_stats()}")
    print(f"Get key1 after adding 4th: {test_cache.get(*key1_args, **key1_kwargs)}")
    print(f"Get key2 after adding 4th: {test_cache.get(*key2_args)}")
    print(f"Get key3 after adding 4th: {test_cache.get(*key3_args, **key3_kwargs)}")

    print("\n测试复杂参数:")
    test_cache.set("complex_value", *key_complex_args)
    print(f"Get complex: {test_cache.get(*key_complex_args)}")

    print("\n清空缓存:")
    test_cache.clear()
    print(f"Cache info: {test_cache.get_stats()}")
    print(f"Get key1 after clear: {test_cache.get(*key1_args, **key1_kwargs)}")