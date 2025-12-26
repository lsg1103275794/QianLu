"""
Error handling utility for GlyphMind service.
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException
from pydantic import BaseModel

# 从validation模块导入异常类为兼容层
from src.validation.error_handler import (
    BaseText2AlpacaError,
    ConfigurationError,
    APIConnectionError,
    APIResponseError as ValidationAPIResponseError,
    APIResponseFormatError,
    APITimeoutError,
    APIError as ValidationAPIError,
    ValidationError as ValidationValidationError,
    APICallError
)

# ----------------- 原始错误定义 -----------------
class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
    code: int

class GlyphMindError(Exception):
    """Base exception class for GlyphMind"""
    def __init__(self, message: str, code: int = 500, detail: Optional[str] = None):
        self.message = message
        self.code = code
        self.detail = detail
        super().__init__(message)

class APIError(GlyphMindError):
    """API related errors"""
    def __init__(self, message: str, code: int = 500, detail: Optional[str] = None, provider_name: str = "Unknown"):
        self.provider_name = provider_name
        super().__init__(message=message, code=code, detail=detail)

class ConfigError(GlyphMindError):
    """Configuration related errors"""
    pass

class ValidationError(GlyphMindError):
    """Validation related errors"""
    pass

class ProviderError(GlyphMindError):
    """Provider related errors"""
    pass

class APIResponseError(GlyphMindError):
    """API响应错误，用于处理API返回的非200状态码或错误响应"""
    def __init__(self, message: str, status_code: int = 500, response_body: Optional[Dict[str, Any]] = None, provider: Optional[str] = None):
        detail = f"Provider: {provider}, Status: {status_code}, Response: {response_body}" if response_body else None
        super().__init__(message=message, code=status_code, detail=detail)
        self.response_body = response_body
        self.provider = provider
        self.status_code = status_code

# ----------------- 处理函数 -----------------
def handle_error(error: Exception) -> Dict[str, Any]:
    """Handle errors and return appropriate response"""
    # 处理本地GlyphMindError
    if isinstance(error, GlyphMindError):
        return {
            "error": error.message,
            "detail": error.detail,
            "code": error.code
        }
    # 处理FastAPI的HTTPException
    elif isinstance(error, HTTPException):
        return {
            "error": error.detail,
            "code": error.status_code
        }
    # 处理validation模块的异常
    elif isinstance(error, BaseText2AlpacaError):
        # 转换validation模块的异常为本地异常
        if isinstance(error, ConfigurationError):
            return handle_error(ConfigError(str(error), 400))
        elif isinstance(error, ValidationAPIError):
            return handle_error(APIError(str(error), 502, provider_name=getattr(error, 'provider_name', 'Unknown')))
        else:
            # 其他validation模块异常
            return {
                "error": str(error),
                "code": 500
            }
    # 兜底处理
    else:
        return {
            "error": "Internal server error",
            "detail": str(error),
            "code": 500
        }

def raise_http_error(status_code: int, message: str, detail: Optional[str] = None) -> None:
    """Raise HTTP exception with error details"""
    raise HTTPException(
        status_code=status_code,
        detail=ErrorResponse(
            error=message,
            detail=detail,
            code=status_code
        ).dict()
    ) 