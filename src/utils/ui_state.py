# src/utils/ui_state.py
import json
from pathlib import Path
import logging
from typing import Dict, Any, Optional
import asyncio # 使用 asyncio 文件锁

# 确定状态文件路径 (项目根目录/data/ui_state.json)
try:
    # __file__ is defined
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
except NameError:
    # __file__ is not defined, e.g., in interactive mode
    PROJECT_ROOT = Path.cwd()

DATA_DIR = PROJECT_ROOT / "data"
UI_STATE_FILE = DATA_DIR / "ui_state.json"
DATA_DIR.mkdir(parents=True, exist_ok=True) # 确保目录存在

logger = logging.getLogger(__name__)

# 简单的内存锁，用于防止并发写入问题 (对于简单应用足够)
# 如果需要更强的跨进程锁，可以考虑 filelock 库
_lock = asyncio.Lock()
_cache: Optional[Dict[str, Any]] = None # 简单的内存缓存

async def _load_state_from_file() -> Dict[str, Any]:
    """从文件加载状态，带缓存"""
    global _cache
    if _cache is not None:
        # 从缓存快速返回
        # logger.debug("Returning UI state from memory cache.")
        return _cache.copy()

    async with _lock:
        # 再次检查缓存，防止在等待锁时其他协程已加载
        if _cache is not None:
             # logger.debug("Returning UI state from memory cache (after lock).")
             return _cache.copy()

        if not UI_STATE_FILE.exists():
            logger.info(f"UI state file not found at {UI_STATE_FILE}, returning empty state.")
            _cache = {}
            return {}
        try:
            # 使用 aiofiles 进行异步文件读写
            import aiofiles
            async with aiofiles.open(UI_STATE_FILE, mode='r', encoding='utf-8') as f:
                content = await f.read()
                if not content: # 文件为空
                    logger.info(f"UI state file {UI_STATE_FILE} is empty.")
                    _cache = {}
                    return {}
                _cache = json.loads(content)
                logger.info(f"Loaded UI state from {UI_STATE_FILE}")
                return _cache.copy()
        except ImportError:
             logger.warning("aiofiles library not found. Falling back to sync file I/O for UI state. Consider installing aiofiles for better performance.")
             # Fallback to sync I/O if aiofiles not installed
             try:
                  with open(UI_STATE_FILE, 'r', encoding='utf-8') as f_sync:
                      content_sync = f_sync.read()
                      if not content_sync:
                          _cache = {}
                          return {}
                      _cache = json.loads(content_sync)
                      logger.info(f"Loaded UI state from {UI_STATE_FILE} (sync fallback)")
                      return _cache.copy()
             except Exception as sync_e:
                  logger.error(f"Error loading UI state (sync fallback) from {UI_STATE_FILE}: {sync_e}", exc_info=True)
                  _cache = {} # Reset cache on error
                  return {}

        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {UI_STATE_FILE}. Returning empty state.", exc_info=True)
            _cache = {} # 重置缓存
            return {}
        except Exception as e:
            logger.error(f"Error loading UI state from {UI_STATE_FILE}: {e}", exc_info=True)
            # 不重置缓存，可能只是临时读取错误
            return _cache.copy() if _cache is not None else {}


async def get_ui_state(page_key: str) -> Optional[Dict[str, Any]]:
    """获取指定页面的 UI 状态"""
    all_states = await _load_state_from_file()
    state = all_states.get(page_key)
    logger.debug(f"Getting UI state for page '{page_key}': {'Found' if state else 'Not Found'}")
    return state

async def save_ui_state(page_key: str, state: Dict[str, Any]) -> bool:
    """保存指定页面的 UI 状态"""
    global _cache
    async with _lock:
        # 确保先加载最新的状态，避免覆盖其他页面的状态
        current_all_states = await _load_state_from_file()
        current_all_states[page_key] = state
        _cache = current_all_states.copy() # 更新缓存

        try:
             # 使用 aiofiles 进行异步文件读写
            import aiofiles
            async with aiofiles.open(UI_STATE_FILE, mode='w', encoding='utf-8') as f:
                await f.write(json.dumps(current_all_states, indent=2, ensure_ascii=False))
            logger.info(f"Saved UI state for page '{page_key}' to {UI_STATE_FILE}")
            return True
        except ImportError:
             logger.warning("aiofiles library not found. Falling back to sync file I/O for UI state saving.")
             # Fallback to sync I/O
             try:
                  with open(UI_STATE_FILE, 'w', encoding='utf-8') as f_sync:
                      json.dump(current_all_states, f_sync, indent=2, ensure_ascii=False)
                  logger.info(f"Saved UI state for page '{page_key}' to {UI_STATE_FILE} (sync fallback)")
                  return True
             except Exception as sync_e:
                  logger.error(f"Error saving UI state (sync fallback) to {UI_STATE_FILE}: {sync_e}", exc_info=True)
                  return False
        except Exception as e:
            logger.error(f"Error saving UI state to {UI_STATE_FILE}: {e}", exc_info=True)
            return False 