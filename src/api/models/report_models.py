from pydantic import BaseModel, Field
from typing import List, Optional

class ReportGenerationRequest(BaseModel):
    topic: str
    model: Optional[str] = Field(None, description="要使用的LLM模型的名称，例如 'llama3'")
    # 后续可以添加:
    # template_id: Optional[str] = None
    # custom_dimensions: Optional[List[str]] = None
    # num_search_results: int = 5

class ReportGenerationResponse(BaseModel):
    report_content: str
    # 后续可以添加:
    # keywords: List[str] = []
    # sources: List[str] = [] 