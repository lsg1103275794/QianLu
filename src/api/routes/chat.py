# src/routers/chat.py

import json
import logging
from typing import List, Optional, Dict, Any, AsyncGenerator
import uuid
import os
from datetime import datetime

from fastapi import APIRouter, HTTPException, Body, status, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, Field

from src.providers import factory
from src.utils.error_handler import handle_error, raise_http_error, APIError
from src.api import auth

日志记录器 = logging.getLogger(__name__)

# --- Pydantic 模型 ---


class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str
    content: str
    timestamp: Optional[str] = None
    
    def get(self, key, default=None):
        """
        实现类似字典的get方法，使其能够与接受字典的函数兼容
        当消息对象需要和字典对象一样处理时使用
        """
        if key == "role":
            return self.role
        elif key == "content":
            return self.content
        elif key == "timestamp":
            return self.timestamp
        return default
        
    def dict(self):
        """返回字典表示，兼容Pydantic v1"""
        return {"role": self.role, "content": self.content}
        
    def model_dump(self):
        """返回字典表示，兼容Pydantic v2"""
        return self.dict()


class ChatRequest(BaseModel):
    provider: str = Field(..., description="API 提供商名称")
    model: str = Field(..., description="模型名称")
    messages: List[ChatMessage] = Field(..., description="包含上下文的聊天消息列表")
    stream: bool = Field(False, description="是否使用流式响应")
    # Add optional generation parameters
    temperature: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="控制生成文本的随机性"
    )
    max_tokens: Optional[int] = Field(
        None, gt=0, description="限制生成的最大 token 数量"
    )
    top_p: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="核采样阈值"
    )
    stop: Optional[List[str]] = Field(
        None, description="停止生成的标记列表"
    )
    # Can add other parameters like top_p as needed


class ChatResponse(BaseModel):
    role: str = Field("assistant", description="响应消息的角色")
    content: str = Field(..., description="助手生成的完整响应内容")
    # Can add fields like model, usage, etc.


# --- API 路由 ---

聊天路由 = APIRouter(
    prefix="/chat",  # Note: prefix in backend_main.py is usually /api/chat
    tags=["聊天"],  # Only defines the / path here
)


async def stream_generator(
    handler: Any, payload: Dict[str, Any]
) -> AsyncGenerator[str, None]:
    """异步生成器，用于处理流式响应并格式化为 SSE。"""
    try:
        # Assume handler.stream_chat is an async generator
        async for chunk in handler.stream_chat(**payload):
            sse_data = None  # Initialize sse_data for each chunk
            if isinstance(chunk, dict):
                # ADDED: Check if this is a statistics block yielded from the handler
                if chunk.get("done") is True and \
                   "prompt_eval_count" in chunk and \
                   "eval_count" in chunk:
                    日志记录器.info(f"Chat route: Received stats block from handler: {json.dumps(chunk, ensure_ascii=False)}")
                    # Pass the stats block as is. The frontend's streamChat function
                    # is designed to parse this specific structure for stats.
                    sse_data = chunk
                # Check for the standard OpenAI format first
                elif (
                    chunk.get("choices")
                    and isinstance(chunk["choices"], list)
                    and len(chunk["choices"]) > 0
                ):
                    delta = chunk["choices"][0].get("delta")
                    if isinstance(delta, dict):
                        # Check if it's the initial role message or content
                        if "role" in delta:
                            sse_data = chunk  # Pass the role chunk as is
                        elif "content" in delta:
                            sse_data = chunk  # Pass the content chunk as is
                        else:
                            日志记录器.warning(
                                f"流式块 delta 中缺少 role 或 content: {delta}"
                            )
                    else:
                        日志记录器.warning(
                            f"流式块 choices[0] 中的 delta 不是字典: {delta}"
                        )
                # Check for direct content or error keys as fallback
                elif "content" in chunk:
                    # 日志记录内容块
                    日志记录器.debug(f"处理内容块: {chunk['content'][:100]}...")
                    # Format into standard structure
                    sse_data = {"choices": [{"delta": {"content": chunk["content"]}}]}
                elif "error" in chunk:
                    sse_data = chunk  # Pass error chunks directly
                else:
                    日志记录器.warning(f"无法识别的字典流式块结构: {chunk}")
                    # Optionally, try sending the raw dict as a fallback
                    # sse_data = chunk

            elif isinstance(chunk, str):
                # If the handler yields raw strings, wrap them
                sse_data = {"choices": [{"delta": {"content": chunk}}]}

            if sse_data is not None:
                # Format as SSE: data: <json_string>\n\n
                sse_formatted = f"data: {json.dumps(sse_data, ensure_ascii=False)}\n\n"
                日志记录器.debug(f"发送 SSE 块: {sse_formatted.strip()}")
                yield sse_formatted
            else:
                # Log if a chunk was received but couldn't be processed
                日志记录器.debug(f"跳过无法处理的流式块: {chunk}")

    except APIError as e:  # 捕获自定义API错误
        日志记录器.error(f"流式处理中 API 错误: {e.message} - {getattr(e, 'details', '')}")
        error_data = {
            "error": {
                "message": e.message,
                "detail": getattr(e, 'details', ''),
                "provider": getattr(e, 'provider_name', 'Unknown Provider')
            }
        }
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    except Exception as e:
        日志记录器.exception(f"流式处理中发生意外错误: {e}")
        # 发送错误事件到前端
        error_data = {"error": {"message": "流式处理时发生内部错误", "detail": str(e)}}
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    finally:
        # 确保总是发送[DONE]标记，以便前端知道流已结束
        日志记录器.info("流式响应生成结束，发送[DONE]标记")
        yield "data: [DONE]\n\n"


@聊天路由.post("/", summary="处理聊天请求 (流式或非流式)", response_model=None)
async def handle_chat(
    request: ChatRequest, 
    background_tasks: BackgroundTasks,
    user_token: str = Depends(auth.get_user_token)
):
    """处理聊天请求并使用API获取响应"""
    # 记录请求开始
    request_id = str(uuid.uuid4())
    日志记录器.info(f"请求ID {request_id} - 开始处理聊天请求，提供商: {request.provider}，模型: {request.model}，请求流式: {request.stream}")
    
    # 获取提供商标识符
    provider_id = request.provider  # 直接使用请求体中的provider字段
    
    # 设置默认响应
    response_data = {"id": request_id, "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}
    
    # 准备工作：创建聊天历史、获取流模式设置
    try:
        # 直接从factory获取最新处理器实例，确保使用最新的.env配置
        try:
            日志记录器.debug(f"为提供商 '{provider_id}' 获取最新处理器实例")
            handler = factory.get_handler(provider_id)
        except ValueError as handler_err:
            日志记录器.error(f"无法获取处理器: {handler_err}")
            raise HTTPException(status_code=400, detail=f"无法获取API处理器: {str(handler_err)}")
        
        # 添加调试日志
        日志记录器.debug(f"请求ID {request_id} - 消息列表: {[type(m).__name__ for m in request.messages]}")
        for i, msg in enumerate(request.messages):
            日志记录器.debug(f"请求ID {request_id} - 消息 #{i}: 类型={type(msg).__name__}, 内容={msg.role}/{msg.content[:30]}...")
        
        # 处理聊天请求 - 使用 request.stream 进行判断
        if request.stream:
            # 流模式
            # 设置流式生成响应
            日志记录器.debug(f"请求ID {request_id} - 使用流模式处理聊天")
            
            # 创建事件生成器
            async def event_generator():
                full_response_content = "" # 初始化用于累积响应内容的变量
                try:
                    # 初始化聊天历史
                    chat_history = request.messages
                    
                    # 添加调试日志
                    日志记录器.debug(f"请求ID {request_id} - 开始流式处理聊天请求, 消息数量: {len(chat_history)}")
                    
                    # 处理流式响应
                    async for chunk in handler.stream_chat(
                        messages=chat_history, 
                        model=request.model,  # 直接使用完整的模型名称
                        temperature=request.temperature,
                        max_tokens=request.max_tokens,
                        top_p=request.top_p,
                        stop=request.stop
                    ):
                        # 累积响应内容
                        # 注意：这里的 chunk 结构依赖于具体的 handler.stream_chat 实现
                        # 假设 chunk 是一个字典，且包含 'choices' -> list -> dict -> 'delta' -> 'content'
                        try:
                            content_delta = chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')
                            if content_delta:
                                full_response_content += content_delta
                        except (IndexError, AttributeError, TypeError) as e:
                             日志记录器.warning(f"请求ID {request_id} - 解析流式块中的内容时出错: {e}, 块: {chunk}")

                        # 添加调试日志
                        日志记录器.debug(f"请求ID {request_id} - 收到流式数据块: {json.dumps(chunk, ensure_ascii=False)[:200]}")
                        
                        # 确保数据被正确JSON序列化，添加所需的SSE行格式
                        json_str = json.dumps(chunk, ensure_ascii=False)
                        sse_formatted = f"data: {json_str}\n\n"
                        日志记录器.debug(f"请求ID {request_id} - 发送SSE格式数据: {sse_formatted.strip()}")
                        yield sse_formatted
                        
                except APIError as api_err:
                    # 处理API错误
                    error_response = {
                        "error": {
                            "message": getattr(api_err, 'message', str(api_err)),
                            "detail": getattr(api_err, 'details', ''),
                            "provider": getattr(api_err, 'provider_name', 'Unknown Provider'),
                            "type": type(api_err).__name__
                        }
                    }
                    error_sse = f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
                    日志记录器.error(f"请求ID {request_id} - API错误: {getattr(api_err, 'message', str(api_err))}")
                    yield error_sse
                except Exception as stream_err:
                    # 将其他异常转换为SSE事件
                    error_response = {
                        "error": {
                            "message": str(stream_err),
                            "type": type(stream_err).__name__
                        }
                    }
                    error_sse = f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
                    日志记录器.error(f"请求ID {request_id} - 流式处理过程中出错: {stream_err}", exc_info=True)
                    日志记录器.debug(f"请求ID {request_id} - 发送错误SSE: {error_sse.strip()}")
                    yield error_sse
                finally:
                    # 确保发送DONE标记
                    yield "data: [DONE]\n\n"
                    日志记录器.info(f"请求ID {request_id} - 流式处理完成，累积内容长度: {len(full_response_content)}")
                    
                    # 可以在这里添加异步任务将完整响应内容保存到数据库等
            
            # 返回流式响应
            日志记录器.debug(f"请求ID {request_id} - 创建EventSourceResponse")
            return EventSourceResponse(
                event_generator(),
                media_type="text/event-stream"
            )
        else:
            # 非流模式
            日志记录器.debug(f"请求ID {request_id} - 使用非流模式处理聊天")
            
            # 初始化聊天历史  
            chat_history = request.messages
            
            # 处理非流式响应
            completion_response = await handler.chat(
                messages=chat_history,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
                stop=request.stop
            )
            
            # 合并响应
            response_data.update(completion_response)
            
            # 记录完成
            日志记录器.info(f"请求ID {request_id} - 聊天请求处理完成 (非流模式)")
            return response_data
            
    except Exception as e:
        # 错误处理
        日志记录器.error(f"请求ID {request_id} - 处理聊天请求时出错: {e}", exc_info=True)
        
        # 构建错误响应
        error_message = str(e)
        error_response = {
            "error": {
                "message": error_message,
                "type": type(e).__name__,
                "param": None,
                "code": None
            }
        }
        
        # 根据异常类型设置响应状态码
        status_code = 500
        if isinstance(e, ValueError):
            status_code = 400
        elif isinstance(e, NotImplementedError):
            status_code = 501
        
        # 如果是HTTP异常，使用其状态码
        if isinstance(e, HTTPException):
            status_code = e.status_code
            
        raise HTTPException(
            status_code=status_code, 
            detail=error_response
        )
