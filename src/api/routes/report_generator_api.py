from fastapi import APIRouter, Depends, HTTPException
from src.api.models.report_models import ReportGenerationRequest, ReportGenerationResponse
# 注意这里的导入，确保 ReportGeneratorService 类本身也被导入，以便类型提示和依赖注入能够正确工作
from src.services.report_generator.service import report_generator_service, ReportGeneratorService 
from src.services.hot_topics.service import HotTopicsService
from src.api.models.hot_topic_models import HotTopicRequest, HotTopicItem
from pydantic import BaseModel
from typing import Optional, List
# 移除错误的 Ollama service 导入
# from src.services.report_generator.ollama_service import generate_ollama_report # Assuming this exists for Ollama 
from src.providers.factory import get_handler # Changed from get_provider_handler
from src.utils.logging import logger
import asyncio

router = APIRouter()

# --- Request Models ---
# 保留原来的 Ollama 请求模型（如果 service 需要）或 Cloud 请求模型
# class OllamaReportRequest(BaseModel): # 可能不再需要，取决于原来的 create_report 如何处理
#     topic: str
#     model: Optional[str] = None

class CloudReportRequest(BaseModel):
    topic: str
    provider: str # Cloud provider is required
    model: Optional[str] = None # Cloud model is optional (use provider default)

# --- 原来的 Ollama/Default 端点 --- 
@router.post("/generate-report", response_model=ReportGenerationResponse)
async def create_report(
    request: ReportGenerationRequest, # 使用原来的请求模型
    service: ReportGeneratorService = Depends(lambda: report_generator_service) 
):
    logger.info(f"Received request for default/Ollama report generation: topic='{request.topic}', model='{request.model or 'service default'}'")
    try:
        # 这个函数处理默认的（可能是Ollama）报告生成
        response = await service.generate_report(request)
        logger.info(f"Successfully generated default/Ollama report for topic: '{request.topic}'")
        return response
    except Exception as e:
        logger.error(f"Error in default/Ollama report endpoint /generate-report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成报告时发生内部服务器错误。") 

# --- 移除冗余的 Ollama 端点 --- 
# @router.post("/generate-report", summary="使用Ollama生成研报")
# async def generate_report_ollama_endpoint(request: OllamaReportRequest):
#     # ... (代码已移除) ...

# --- New Cloud API Endpoint --- 
# 注意：路径修改为 /generate/cloud 以区别于默认/Ollama端点
@router.post("/generate/cloud", summary="使用云端API生成研报")
async def generate_report_cloud_endpoint(request: CloudReportRequest):
    logger.info(f"Received request for Cloud report generation: topic='{request.topic}', provider='{request.provider}', model='{request.model or 'provider default'}'")
    try:
        # 1. Get the appropriate provider handler
        handler = get_handler(request.provider) # Changed from get_provider_handler
        if not handler:
            logger.error(f"No handler found for provider: {request.provider}")
            raise HTTPException(status_code=400, detail=f"未找到或配置服务商: {request.provider}")

        # 2. Check if the handler supports report generation (example method name)
        #    根据你的 Provider Handler 实际情况调整方法名 'generate_report'
        if not hasattr(handler, 'generate_report'):
             logger.error(f"Handler for provider '{request.provider}' does not support 'generate_report' method.")
             raise HTTPException(status_code=501, detail=f"服务商 '{request.provider}' 不支持此生成功能。")

        # 3. Call the handler's generation method
        logger.info(f"Calling generate_report on handler for '{request.provider}' with model '{request.model or 'provider default'}'")
        report_content = await handler.generate_report(topic=request.topic, model=request.model)
        
        logger.info(f"Successfully generated Cloud report via '{request.provider}' for topic: '{request.topic}'")
        # 确保返回格式与前端期望一致，例如 {"report_content": ...}
        # 如果 generate_report 直接返回字符串:
        return {"report_content": report_content} 
        # 如果 generate_report 返回一个包含内容的字典:
        # return report_content 

    except HTTPException as http_exc: # Re-raise known HTTP exceptions
        raise http_exc
    except Exception as e:
        logger.error(f"Error generating Cloud report via '{request.provider}' for topic '{request.topic}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成云端研报时出错: {str(e)}") 

# --- 新增：使用热点话题数据生成研报 ---
class HotTopicsReportRequest(BaseModel):
    hot_topic_keywords: str  # 关键词，用于筛选相关热点话题
    model: Optional[str] = None  # 使用的LLM模型
    max_topics: int = 5  # 最多包含的热点话题数

@router.post("/generate-from-hot-topics", response_model=ReportGenerationResponse, summary="基于热点话题生成研报")
async def generate_report_from_hot_topics(
    request: HotTopicsReportRequest,
    service: ReportGeneratorService = Depends(lambda: report_generator_service)
):
    logger.info(f"收到基于热点话题生成研报请求：关键词='{request.hot_topic_keywords}', 模型='{request.model or '默认'}'")
    
    try:
        # 1. 获取热点话题
        hot_topics_service = HotTopicsService()
        hot_topic_request = HotTopicRequest(count=10)  # 获取更多话题以便筛选
        
        try:
            topics = await hot_topics_service.get_hot_topics(hot_topic_request)
            logger.info(f"成功获取到 {len(topics)} 个热点话题")
            
            # 2. 筛选与关键词相关的话题
            keywords = request.hot_topic_keywords.lower().split()
            filtered_topics = []
            
            for topic in topics:
                # 检查标题或摘要是否包含关键词
                title_lower = topic.title.lower()
                summary_lower = (topic.summary or "").lower()
                
                if any(kw in title_lower or kw in summary_lower for kw in keywords):
                    filtered_topics.append(topic)
                    if len(filtered_topics) >= request.max_topics:
                        break
            
            logger.info(f"筛选出 {len(filtered_topics)} 个与关键词 '{request.hot_topic_keywords}' 相关的热点话题")
            
            if not filtered_topics:
                logger.warning(f"未找到与关键词 '{request.hot_topic_keywords}' 相关的热点话题")
                return ReportGenerationResponse(
                    report_content=f"未找到与关键词 '{request.hot_topic_keywords}' 相关的热点话题。请尝试使用其他关键词。"
                )
            
            # 3. 将筛选后的热点话题转换为搜索结果格式
            search_results = []
            for topic in filtered_topics:
                search_results.append({
                    "title": topic.title,
                    "url": str(topic.source_url) if topic.source_url else "",
                    "snippet": topic.summary or topic.title,
                    "source_name": f"{topic.source_name}（热点话题）"
                })
            
            # 4. 生成研报
            # 构建新的请求参数
            report_request = ReportGenerationRequest(
                topic=f"基于热点话题的研报：{request.hot_topic_keywords}",
                model=request.model
            )
            
            # 调用LLM生成研报
            llm_generated_content = await service._call_llm(
                report_request.topic, 
                search_results, 
                model_name=report_request.model
            )
            
            logger.info(f"成功基于热点话题生成研报，关键词: '{request.hot_topic_keywords}'")
            return ReportGenerationResponse(report_content=llm_generated_content)
            
        except Exception as e:
            logger.exception(f"获取或处理热点话题时出错: {e}")
            return ReportGenerationResponse(
                report_content=f"获取或处理热点话题时出错: {str(e)}"
            )
    
    except Exception as e:
        logger.exception(f"生成基于热点话题的研报时出错: {e}")
        raise HTTPException(status_code=500, detail=f"生成研报时发生服务器错误: {str(e)}") 