import os
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import uuid
import re

# Define the base data directory relative to this file's location or using environment variables
# Assuming this file is in src/routers/, DATA_DIR should point to G:\Aigc\test\​GlyphMind\data
# Adjust the path resolution as needed based on your project structure
try:
    # Assuming the script runs from the project root or DATA_DIR is set
    DATA_DIR = Path(os.getenv("DATA_DIR", "data")).resolve()
except Exception:
    # Fallback if running from unexpected location, adjust accordingly
    DATA_DIR = Path("../data").resolve()

LOGS_DIR = DATA_DIR / "output" / "logs"

# Ensure logs directory exists
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Define Pydantic models for response structures
class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[datetime] = None

# 新增：用于保存聊天历史的请求模型
class SaveChatLogRequest(BaseModel):
    provider: str
    model: str
    messages: List[Dict[str, Any]]
    timestamp: Optional[str] = None

class ChatLogSummary(BaseModel):
    id: str # filename without .json
    timestamp: datetime
    provider: Optional[str] = "Unknown"
    model: Optional[str] = "Unknown"
    messages_count: int = 0
    first_user_message: Optional[str] = None # Preview of the first user message

class ChatLogDetail(BaseModel):
    id: str
    provider: Optional[str] = "Unknown"
    model: Optional[str] = "Unknown"
    timestamp: datetime
    messages: List[ChatMessage]

# 新增：保存聊天记录响应模型
class SaveChatLogResponse(BaseModel):
    id: str
    status: str = "success"
    message: str = "Chat log saved successfully"

# Create the router
router = APIRouter(
    tags=["Chat History"],
    prefix="/chat-logs" # Prefix for all routes in this file
)

@router.get("", response_model=List[ChatLogSummary], summary="Get list of chat logs")
async def get_chat_logs_list():
    """
    Retrieves a summary list of all saved chat logs.
    Reads metadata from each JSON log file.
    """
    summaries: List[ChatLogSummary] = []
    if not LOGS_DIR.exists():
        # If the directory doesn't exist, return empty list immediately
        return summaries
        
    log_files = sorted(
        LOGS_DIR.glob("*.json"), 
        key=os.path.getmtime, 
        reverse=True # Show newest first
    )

    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            
            # Extract metadata - handle potential missing keys gracefully
            messages = log_data.get("messages", [])
            first_user_msg_content = next((msg.get("content") for msg in messages if msg.get("role") == "user"), None)
            
            # Try to parse timestamp, fallback to file modification time
            log_timestamp_str = log_data.get("timestamp")
            if log_timestamp_str:
                try:
                    log_timestamp = datetime.fromisoformat(log_timestamp_str.replace('Z', '+00:00')) # Handle Z suffix
                except ValueError:
                    log_timestamp = datetime.fromtimestamp(log_file.stat().st_mtime)
            else:
                log_timestamp = datetime.fromtimestamp(log_file.stat().st_mtime)

            summary = ChatLogSummary(
                id=log_file.stem, # Use filename without extension as ID
                timestamp=log_timestamp,
                provider=log_data.get("provider", "Unknown"),
                model=log_data.get("model", "Unknown"),
                messages_count=len(messages),
                first_user_message=first_user_msg_content[:100] if first_user_msg_content else None # Truncate preview
            )
            summaries.append(summary)
        except Exception as e:
            print(f"Error processing log file {log_file.name}: {e}") # Log error for debugging
            # Optionally skip corrupted files or add an error indicator
            continue
            
    return summaries

@router.get("/{chat_id}", response_model=ChatLogDetail, summary="Get chat log details")
async def get_chat_log_detail(chat_id: str):
    """
    Retrieves the full content of a specific chat log by its ID (filename).
    """
    # Sanitize chat_id to prevent directory traversal
    if ".." in chat_id or "/" in chat_id or "\\" in chat_id:
        raise HTTPException(status_code=400, detail="Invalid chat ID format.")
        
    log_file = LOGS_DIR / f"{chat_id}.json"

    if not log_file.exists() or not log_file.is_file():
        raise HTTPException(status_code=404, detail=f"Chat log with ID '{chat_id}' not found.")

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
            
        # Basic validation of loaded data structure
        if not isinstance(log_data, dict) or "messages" not in log_data:
             raise HTTPException(status_code=500, detail=f"Invalid format in chat log file: {chat_id}.json")

        # Try to parse timestamp, fallback to file modification time
        log_timestamp_str = log_data.get("timestamp")
        if log_timestamp_str:
            try:
                log_timestamp = datetime.fromisoformat(log_timestamp_str.replace('Z', '+00:00'))
            except ValueError:
                 log_timestamp = datetime.fromtimestamp(log_file.stat().st_mtime)
        else:
             log_timestamp = datetime.fromtimestamp(log_file.stat().st_mtime)
             
        # Ensure messages are in the correct format
        messages_data = log_data.get("messages", [])
        parsed_messages = []
        for msg in messages_data:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                 msg_timestamp_raw = msg.get("timestamp")
                 parsed_msg_timestamp = None
                 
                 if msg_timestamp_raw is not None:
                     if isinstance(msg_timestamp_raw, (int, float)):
                         # Assume it's a Unix timestamp, potentially in milliseconds
                         try:
                             # Convert to seconds if it seems to be in milliseconds
                             timestamp_in_seconds = msg_timestamp_raw
                             if msg_timestamp_raw > 10**12: # A simple heuristic: if it's a large number, likely milliseconds
                                 timestamp_in_seconds = msg_timestamp_raw / 1000.0
                             parsed_msg_timestamp = datetime.fromtimestamp(timestamp_in_seconds)
                         except (ValueError, OSError) as e: # Added OSError for Errno 22
                             print(f"Warning: Could not convert numeric timestamp {msg_timestamp_raw} (seconds: {timestamp_in_seconds if 'timestamp_in_seconds' in locals() else 'N/A'}) to datetime: {e}")
                             pass # Keep as None
                     elif isinstance(msg_timestamp_raw, str):
                         try:
                             parsed_msg_timestamp = datetime.fromisoformat(msg_timestamp_raw.replace('Z', '+00:00'))
                         except ValueError:
                             print(f"Warning: Could not parse ISO string timestamp {msg_timestamp_raw}.")
                             pass # Keep as None
                     else:
                         print(f"Warning: Unexpected type for timestamp {msg_timestamp_raw}: {type(msg_timestamp_raw)}")

                 # Ensure content is a string
                 msg_content = msg.get("content")
                 if not isinstance(msg_content, str):
                     print(f"Warning: Message content is not a string (type: {type(msg_content)}), converting to string. Value: {msg_content}")
                     msg_content = str(msg_content)

                 parsed_messages.append(ChatMessage(
                     role=str(msg.get("role")), # Ensure role is also string
                     content=msg_content,
                     timestamp=parsed_msg_timestamp
                 ))
            else:
                 # Handle potentially malformed message entries
                 print(f"Skipping malformed message in {chat_id}.json: {msg}")


        return ChatLogDetail(
            id=chat_id,
            provider=log_data.get("provider", "Unknown"),
            model=log_data.get("model", "Unknown"),
            timestamp=log_timestamp,
            messages=parsed_messages
        )
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Error decoding JSON from chat log file: {chat_id}.json")
    except Exception as e:
        print(f"Error reading chat log file {log_file.name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read chat log details: {e}") 

# 新增：保存聊天记录端点
@router.post("", response_model=SaveChatLogResponse, summary="Save chat log")
async def save_chat_log(chat_log: SaveChatLogRequest):
    """
    保存聊天记录到文件系统。
    自动生成唯一ID并返回。
    """
    try:
        # 确保目录存在
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        
        # 生成唯一ID
        chat_id = str(uuid.uuid4())
        
        # 准备保存的数据
        current_time = datetime.utcnow().isoformat() + "Z"
        save_data = {
            "id": chat_id,
            "provider": chat_log.provider,
            "model": chat_log.model,
            "timestamp": chat_log.timestamp or current_time,
            "messages": chat_log.messages
        }
        
        # 处理模型名中的特殊字符，Windows不允许在文件名中使用的字符
        safe_model_name = re.sub(r'[\\/*?:"<>|]', '_', chat_log.model)
        
        # 生成包含时间戳和模型信息的文件名
        time_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{time_prefix}_{safe_model_name}_{chat_id[:8]}.json"
        
        # 保存到文件
        file_path = LOGS_DIR / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
            
        print(f"Chat log saved successfully to {file_path}")
        
        return SaveChatLogResponse(
            id=chat_id,
            status="success",
            message=f"Chat log saved successfully with ID: {chat_id}"
        )
    except Exception as e:
        print(f"Error saving chat log: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save chat log: {str(e)}") 