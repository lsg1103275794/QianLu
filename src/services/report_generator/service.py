from src.api.models.report_models import ReportGenerationRequest, ReportGenerationResponse
from src.services.hot_topics.handler import perform_web_search
from src.services.hot_topics.service import HotTopicsService
from src.api.models.hot_topic_models import HotTopicRequest
import asyncio
import os
from typing import List, Dict, Any, Optional
import json

# 导入Provider Factory中的get_handler
from src.providers.factory import get_handler, initialize_handlers
from src.providers.base import BaseAPIHandler # 用于类型提示
from src.utils.logging import logger # 使用项目统一的logger

# 确保在服务实例化时或应用启动时，handlers已经被初始化
# 可以在模块级别调用一次，或者确保在 FastAPI startup 事件中调用
# initialize_handlers() # 考虑将其移到 FastAPI 的 startup 事件中，避免多次调用


class ReportGeneratorService:
    async def _call_llm(self, topic: str, search_results: List[Dict[str, Any]], model_name: Optional[str] = None) -> str:
        """
        调用Ollama Local LLM来根据搜索结果生成研报内容。
        """
        # Use the new dedicated handler
        handler_name = "ollama_report_handler"
        logger.info(f"准备调用 '{handler_name}' 为主题 '{topic}' 生成研报... 使用模型: {model_name or 'handler default'}")

        try:
            handler: Optional[BaseAPIHandler] = get_handler(handler_name)
            if not handler:
                error_msg = f"无法获取 '{handler_name}' provider handler。请检查配置和 providers_meta.json。"
                logger.error(error_msg)
                return f"[LLM错误] {error_msg}"
            if not hasattr(handler, 'chat'):
                error_msg = f"'{handler_name}' 实例没有 'chat' 方法。"
                logger.error(error_msg)
                return f"[LLM错误] {error_msg}"
        except Exception as e:
            logger.exception(f"获取 '{handler_name}' 时发生错误: {e}")
            return f"[LLM错误] 初始化LLM Provider '{handler_name}' 时出错: {e}"

        # 2. 整合搜索到的文本内容，为LLM准备上下文
        context_parts = []
        for i, res in enumerate(search_results):
            item_context = f"""搜索结果 {i+1}:
  标题: {res.get('title', 'N/A')}
  URL: {res.get('url', 'N/A')}
  摘要: {res.get('snippet', 'N/A')}
""" # Using triple-quoted f-string for multi-line content
            context_parts.append(item_context)
        concatenated_context = "\n---\n".join(context_parts)

        # 3. 设计Prompt (与之前类似，但现在是真实调用)
        system_prompt = (
            "你是一位直接输出结果的专业行业分析师。你的唯一任务是严格按照用户提供的资料和以下结构，生成一份Markdown格式的研报。不要添加任何解释、开场白、思考过程或总结性发言。直接开始输出研报正文。\n\n" 
            "研报结构：\n"
            "1. 核心摘要：对整个主题和关键发现进行高度概括。\n"
            "2. 主要观点：列出3-5个基于所提供资料的最重要观点或发现。\n"
            "3. 数据支撑（可选）：如果资料中包含具体数据，请提及。\n"
            "4. 潜在影响或未来趋势：基于资料进行简要推测。\n"
            "5. 关键信息来源：列出报告中引用的主要信息来源的标题和URL。\n"
            "6. 关键词：提取5-7个核心关键词。\n\n"
            "再次强调：严格按照以上结构直接输出Markdown研报，不要有任何额外内容。"
        )
        
        user_prompt = (
            f"请为我生成一份关于主题 “{topic}” 的研报。\n"
            "以下是相关的网络搜索摘要作为参考资料：\n\n"
            f"{concatenated_context}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            effective_model_name = model_name
            logger.info(f"向 '{handler_name}' (模型: '{effective_model_name or (handler.default_model if hasattr(handler, 'default_model') else '默认')}') 发送请求...")
            
            llm_response_dict: Dict[str, Any] = await handler.chat(messages=messages, model=effective_model_name)
            
            # This parsing logic should now align with what OllamaReportHandler.chat returns
            if llm_response_dict and 'choices' in llm_response_dict and llm_response_dict['choices']:
                first_choice = llm_response_dict['choices'][0]
                if 'message' in first_choice and 'content' in first_choice['message']:
                    generated_text = first_choice['message']['content'].strip() # .strip() is good, _remove_think_tags in handler also strips
                    logger.info(f"'{handler_name}' 成功生成内容，长度: {len(generated_text)}")
                    return generated_text
                else:
                    error_msg = "LLM响应格式不正确：缺少 message 或 content 键 (在 choices 内)。"
                    logger.error(f"{error_msg} 响应: {json.dumps(llm_response_dict, indent=2, ensure_ascii=False)}")
                    return f"[LLM错误] {error_msg}"
            else:
                error_msg = f"来自 '{handler_name}' 的LLM响应格式不正确或choices为空。"
                logger.error(f"{error_msg} 响应: {json.dumps(llm_response_dict, indent=2, ensure_ascii=False)}")
                return f"[LLM错误] {error_msg}"

        except Exception as e:
            active_model_for_log = model_name or (handler.default_model if hasattr(handler, 'default_model') else 'handler_default')
            logger.exception(f"调用 '{handler_name}' (模型: '{active_model_for_log}') 时发生错误: {e}")
            return f"[LLM错误] 调用LLM ('{handler_name}') 分析内容时出错: {str(e)}"


    async def generate_report(self, request: ReportGenerationRequest) -> ReportGenerationResponse:
        logger.info(f"[ReportGeneratorService] 收到主题请求 (LLM增强版): {request.topic}, 模型: {request.model or '使用默认'}")

        try:
            # 使用两种方式获取数据：1. 直接网络搜索 2. 热点话题服务
            # 1. 直接网络搜索
            search_results = await perform_web_search(query=request.topic, lang="zh-CN", num_results=3)
            
            # 2. 从热点话题服务获取相关数据
            hot_topics_service = HotTopicsService()
            hot_topic_request = HotTopicRequest(count=5)  # 获取5个热点话题
            try:
                hot_topics = await hot_topics_service.get_hot_topics(hot_topic_request)
                
                # 将热点话题转换为搜索结果格式，并添加到搜索结果中
                for topic in hot_topics:
                    # 只添加与请求主题相关的热点（简单关键词匹配）
                    if any(kw in topic.title.lower() for kw in request.topic.lower().split()):
                        topic_result = {
                            "title": topic.title,
                            "url": str(topic.source_url) if topic.source_url else "",
                            "snippet": topic.summary or "（无摘要）",
                            "source_name": f"{topic.source_name}（热点话题）"
                        }
                        search_results.append(topic_result)
                        logger.info(f"从热点话题服务添加了相关信息: {topic.title}")
            except Exception as e:
                logger.warning(f"获取热点话题时出错，将仅使用网络搜索结果: {e}")
        except Exception as e:
            logger.exception(f"[ReportGeneratorService] 获取数据期间出错: {e}")
            return ReportGenerationResponse(report_content=f"为主题 '{request.topic}' 获取数据时出错: {e}")

        if not search_results:
            logger.warning(f"未能找到关于主题 '{request.topic}' 的信息（用于LLM分析）")
            return ReportGenerationResponse(report_content=f"未能找到关于主题 '{request.topic}' 的信息（用于LLM分析）")
        
        llm_generated_content = await self._call_llm(request.topic, search_results, model_name=request.model)
        
        logger.info(f"[ReportGeneratorService] 已为主题生成LLM研报: {request.topic}")
        return ReportGenerationResponse(report_content=llm_generated_content)

report_generator_service = ReportGeneratorService() 