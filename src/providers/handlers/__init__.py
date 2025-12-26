"""
API handler implementations for different providers.
"""
# 移除对base的导入，打破循环依赖
# from ..base import BaseAPIHandler
from .deepseek_ai import DeepseekAIHandler
from .ollama_local import OllamaLocalHandler
from .silicon_flow import SiliconFlowHandler
from .volc_engine import VolcEngineHandler
from .google_gemini import GoogleGeminiHandler
from .zhipu_ai import ZhipuAIHandler
from .ollama_report_handler import OllamaReportHandler

__all__ = [
    # 'BaseAPIHandler',  # 移除BaseAPIHandler
    'DeepseekAIHandler',
    'OllamaLocalHandler',
    'SiliconFlowHandler',
    'VolcEngineHandler',
    'GoogleGeminiHandler',
    'ZhipuAIHandler',
    'OllamaReportHandler'
] 