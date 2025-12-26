"""
Analysis-related Pydantic models.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# --- General Analysis Models ---

class AnalysisRequest(BaseModel):
    text: str = Field(..., description="要分析的文本")
    file_path: Optional[str] = Field(None, description="Optional path to an uploaded file")
    analysis_type: str = Field("basic", description="分析类型 ('basic' or 'deep')")
    options: List[str] = Field(..., description="选择的分析选项/维度")
    api_provider: Optional[str] = Field(None, description="深度分析时选择的 API 提供商")
    model: Optional[str] = Field(None, description="深度分析时选择的模型")
    template: Optional[str] = Field(None, description="深度分析时选择的模板 ID")
    # uploadedFilePath: Optional[str] = Field(None, description="Path of the uploaded file on the server (internal use)")

class AnalysisResponse(BaseModel):
    # Define fields based on what your analysis returns
    # Example for basic analysis:
    sentiment: Optional[Dict[str, Any]] = None
    readability: Optional[Dict[str, Any]] = None
    text_stats: Optional[Dict[str, Any]] = None
    word_frequency: Optional[Dict[str, Any]] = None
    sentence_pattern: Optional[Dict[str, Any]] = None
    keyword_extraction: Optional[Dict[str, Any]] = None
    language_features: Optional[Dict[str, Any]] = None
    # Example for deep analysis (might be just a string or structured dict)
    deep_analysis_report: Optional[Any] = None 

class AnalysisTemplate(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    prompt_template: Optional[str] = None # Full prompt might be loaded separately

# --- V2 Literature Analysis Models ---

class LiteratureAnalysisRequest(BaseModel):
    provider: str = Field(..., description="选择的 API 提供商名称")
    model: str = Field(..., description="选择的模型名称")
    text: str = Field(..., description="待分析的文本内容")
    selected_dimensions: List[str] = Field(
        ...,
        description="用户选择的分析维度 ID 列表 (叶子节点，例如 'rhetorical_devices.metaphor.metaphor_type')",
        example=["rhetorical_devices.metaphor.metaphor_type", "narrative_techniques.perspective_switch.switch_points"]
    )

class LiteratureAnalysisResponse(BaseModel):
    result: str = Field(..., description="AI 返回的分析结果 (可能是 Markdown 或 JSON 字符串)") 