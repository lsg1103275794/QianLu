"""
提供商相关的API路由
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional, Tuple, Literal, Union
import logging
import os
from pydantic import BaseModel, Field
import re
import asyncio
import copy
import dotenv
import json
import aiohttp
from pathlib import Path # Ensure Path is imported

# 移除对 ConfigManager 的直接依赖
# from src.utils.config import ConfigManager 
from src.providers.factory import (
    get_handler,
    get_handler_classes,
    get_handler_for_provider,
    get_all_provider_metadata,
    get_provider_metadata,
    standardize_provider_name,
    _PROJECT_ROOT
)
# Import API Manager instance only for routes that need it (save/schema)
from src.config.api_manager import api_manager

from src.utils.logging import logger as 日志记录器
from src.utils.cache import cache as 缓存管理器
from src.validation.error_handler import APIError, ConfigurationError

# --- Schema Definitions ---
class SelectOption(BaseModel):
    label: str
    value: str

class ConfigItemSchema(BaseModel):
    env_var: str = Field(..., description="对应的环境变量名")
    label: str = Field(..., description="在 UI 中显示的标签")
    description: Optional[str] = Field(None, description="配置项的详细说明")
    type: Literal['text', 'password', 'number', 'boolean', 'select'] = Field(..., description="输入控件类型")
    required: bool = Field(False, description="是否为必填项")
    default: Optional[Union[str, int, float, bool]] = Field(None, description="默认值")
    options: Optional[List[SelectOption]] = Field(None, description="当类型为 'select' 时的选项")
    category: Optional[Literal['basic', 'credentials', 'model_params', 'endpoint']] = Field('basic', description="配置项分类")
    min_value: Optional[Union[int, float]] = Field(None, description="数字类型的最小值")
    max_value: Optional[Union[int, float]] = Field(None, description="数字类型的最大值")
    step_value: Optional[Union[int, float]] = Field(None, description="数字类型的步长")

class ProviderSchema(BaseModel):
    provider_name: str
    display_name: str
    config_items: List[ConfigItemSchema]

class SettingsSchemaResponse(BaseModel):
    global_settings: List[ConfigItemSchema]
    provider_settings: Dict[str, ProviderSchema] # Key is provider_name

class TestModelRequest(BaseModel): # Added TestModelRequest Pydantic Model
    """测试模型连接请求"""
    provider: str
    model: str
    prompt: Optional[str] = None

# --- Schema Data (Remains the same, defined in this file) ---
# 通用设置 Schema
GLOBAL_SCHEMA: List[ConfigItemSchema] = [
    ConfigItemSchema(
        env_var="DEFAULT_PROVIDER",
        label="默认 API 提供商",
        description="选择一个全局默认使用的 API 提供商。",
        type="select", # 需要动态填充 options
        category="basic"
    ),
]

# 各提供商 Schema (Make sure this is complete and correct)
PROVIDER_SCHEMAS: Dict[str, List[ConfigItemSchema]] = {
    "ollama_local": [
        ConfigItemSchema(env_var="OLLAMA_ENDPOINT", label="服务地址", description="Ollama API 服务的地址 (例如 http://localhost:11434)", type="text", required=True, category="endpoint"),
        ConfigItemSchema(env_var="OLLAMA_DEFAULT_MODEL", label="默认模型", description="默认使用的 Ollama 模型名称", type="text", category="basic"),
        ConfigItemSchema(
            env_var="OLLAMA_TEMPERATURE",
            label="Temperature",
            description="控制生成文本的随机性 (例如 0.7)。",
            type="number",
            required=False,
            category="model_params",
            min_value=0.0,
            max_value=2.0,
            step_value=0.1
        ),
        ConfigItemSchema(
            env_var="OLLAMA_MAX_TOKENS",
            label="Max Tokens",
            description="限制单次请求生成的最大 token 数量。",
            type="number",
            required=False,
            category="model_params",
            min_value=1,
            step_value=1
        ),
        ConfigItemSchema(env_var="OLLAMA_TOP_P", label="Top P", description="核采样阈值 (0-1)", type="number", default=0.9, min_value=0, max_value=1, step_value=0.05, category="model_params"),
    ],
    "google_gemini": [
        ConfigItemSchema(env_var="GOOGLE_API_KEY", label="API 密钥", description="你的 Google AI Studio API 密钥", type="password", required=True, category="credentials"),
        ConfigItemSchema(env_var="GOOGLE_DEFAULT_MODEL", label="默认模型", description="默认使用的 Gemini 模型", type="select", default="gemini-1.5-flash-latest", category="basic", options=[
            SelectOption(label="Gemini 1.5 Flash", value="gemini-1.5-flash-latest"),
            SelectOption(label="Gemini 1.5 Pro", value="gemini-1.5-pro-latest"),
            SelectOption(label="Gemini 1.0 Pro", value="gemini-1.0-pro-latest"),
        ]),
        ConfigItemSchema(
            env_var="GOOGLE_TEMPERATURE",
            label="Temperature",
            description="控制生成文本的随机性 (例如 0.7)。",
            type="number",
            required=False,
            category="model_params",
            min_value=0.0,
            max_value=1.0,
            step_value=0.1
        ),
        ConfigItemSchema(
            env_var="GOOGLE_MAX_TOKENS",
            label="Max Tokens",
            description="限制单次请求生成的最大 token 数量 (映射到 max_output_tokens)。",
            type="number",
            required=False,
            category="model_params",
            min_value=1,
            step_value=1
        ),
        ConfigItemSchema(env_var="GOOGLE_TOP_P", label="Top P", description="核采样阈值 (0-1)", type="number", default=0.9, min_value=0, max_value=1, step_value=0.05, category="model_params"),
        ConfigItemSchema(env_var="GOOGLE_TOP_K", label="Top K", description="Top-K 采样 (例如 40)", type="number", category="model_params"),
        # Note: GOOGLE_APPLICATION_CREDENTIALS is not typically user-configured via UI, so not included here.
    ],
    "deepseek_ai": [
        ConfigItemSchema(env_var="DEEPSEEK_API_KEY", label="API 密钥", description="你的 DeepSeek API 密钥", type="password", required=True, category="credentials"),
        ConfigItemSchema(env_var="DEEPSEEK_ENDPOINT", label="端点地址", description="DeepSeek API 端点 (通常不需要修改)", type="text", default="https://api.deepseek.com", category="endpoint"),
        ConfigItemSchema(env_var="DEEPSEEK_DEFAULT_MODEL", label="默认模型", description="默认使用的 DeepSeek 模型", type="text", default="deepseek-chat", category="basic"),
        ConfigItemSchema(
            env_var="DEEPSEEK_TEMPERATURE",
            label="Temperature",
            description="控制生成文本的随机性 (例如 0.7)。",
            type="number",
            required=False,
            category="model_params",
            min_value=0.0,
            max_value=2.0,
            step_value=0.1
        ),
        ConfigItemSchema(
            env_var="DEEPSEEK_MAX_TOKENS",
            label="Max Tokens",
            description="限制单次请求生成的最大 token 数量。",
            type="number",
            required=False,
            category="model_params",
            min_value=1,
            step_value=1
        ),
        ConfigItemSchema(env_var="DEEPSEEK_TOP_P", label="Top P", description="核采样阈值 (0-1)", type="number", default=0.9, min_value=0, max_value=1, step_value=0.05, category="model_params"),
    ],
    "zhipu_ai": [
        ConfigItemSchema(env_var="ZHIPU_API_KEY", label="API 密钥", description="你的智谱 AI API 密钥", type="password", required=True, category="credentials"),
        ConfigItemSchema(env_var="ZHIPU_ENDPOINT", label="端点地址", description="智谱 AI API 端点 (通常不需要修改)", type="text", default="https://open.bigmodel.cn/api/paas/v4/chat/completions", category="endpoint"),
        ConfigItemSchema(env_var="ZHIPU_DEFAULT_MODEL", label="默认模型", description="默认使用的智谱模型 (例如 glm-4, glm-3-turbo)", type="text", default="glm-4", category="basic"),
        ConfigItemSchema(
            env_var="ZHIPU_TEMPERATURE",
            label="Temperature",
            description="控制生成文本的随机性 (0.01 ~ 1.0)。",
            type="number",
            required=False,
            category="model_params",
            min_value=0.01,
            max_value=1.0,
            step_value=0.05
        ),
        ConfigItemSchema(
            env_var="ZHIPU_MAX_TOKENS",
            label="Max Tokens",
            description="限制单次请求生成的最大 token 数量。",
            type="number",
            required=False,
            category="model_params",
            min_value=1,
            step_value=1
        ),
        ConfigItemSchema(env_var="ZHIPU_TOP_P", label="Top P", description="核采样阈值 (0-1, 不能为1)", type="number", default=0.9, min_value=0.01, max_value=0.99, step_value=0.05, category="model_params"),
    ],
    "silicon_flow": [
         ConfigItemSchema(env_var="SILICONFLOW_API_KEY", label="API 密钥", description="你的 SiliconFlow API 密钥", type="password", required=True, category="credentials"),
         ConfigItemSchema(env_var="SILICONFLOW_ENDPOINT", label="端点地址", description="SiliconFlow API 端点", type="text", default="https://api.siliconflow.cn/v1", category="endpoint"),
         ConfigItemSchema(env_var="SILICONFLOW_DEFAULT_MODEL", label="默认模型", description="默认使用的模型", type="text", category="basic"),
        ConfigItemSchema(
            env_var="SILICONFLOW_TEMPERATURE",
            label="Temperature",
            description="控制生成文本的随机性 (例如 0.7)。",
            type="number",
            required=False,
            category="model_params",
            min_value=0.0,
            max_value=2.0,
            step_value=0.1
        ),
        ConfigItemSchema(
            env_var="SILICONFLOW_MAX_TOKENS",
            label="Max Tokens",
            description="限制单次请求生成的最大 token 数量。",
            type="number",
            required=False,
            category="model_params",
            min_value=1,
            step_value=1
        ),
        ConfigItemSchema(env_var="SILICONFLOW_TOP_P", label="Top P", description="核采样阈值 (0-1)", type="number", default=0.9, min_value=0, max_value=1, step_value=0.05, category="model_params"),
    ],
     "volc_engine": [
         # --- 修改：更新 Schema 以匹配 HTTP Bearer Token 认证方式 --- 
         ConfigItemSchema(
             env_var="VOLC_API_KEY", 
             label="API 密钥", 
             description="你的火山方舟 API 密钥", 
             type="password", 
             required=True, 
             category="credentials"
         ),
         ConfigItemSchema(
             env_var="VOLC_ENDPOINT",
             label="端点地址",
             description="火山方舟 API 端点 (例如 https://ark.cn-beijing.volces.com/api/v3/chat/completions)", 
             type="text",
             required=True, 
             category="endpoint"
         ),
         ConfigItemSchema(
             env_var="VOLC_DEFAULT_MODEL", 
             label="模型端点ID (Model ID)",
             description="要使用的模型 Endpoint ID (例如 doubao-pro-128k)", 
             type="text", 
             required=True, 
             category="basic"
         ),
         ConfigItemSchema(
            env_var="VOLC_TEMPERATURE",
            label="Temperature",
            description="控制生成文本的随机性 (0 ~ 1)。",
            type="number",
            required=False,
            category="model_params",
            min_value=0.0,
            max_value=1.0,
            step_value=0.1
        ),
        ConfigItemSchema(
            env_var="VOLC_MAX_TOKENS",
            label="Max Tokens",
            description="限制单次请求生成的最大 token 数量。",
            type="number",
            required=False,
            category="model_params",
            min_value=1,
            step_value=1
        ),
        ConfigItemSchema(env_var="VOLC_TOP_P", label="Top P", description="核采样阈值 (0-1)", type="number", default=0.9, min_value=0, max_value=1, step_value=0.05, category="model_params"),
        ConfigItemSchema(
            env_var="VOLC_REQUEST_TIMEOUT", 
            label="请求超时 (秒)",
            description="API 请求的超时时间（秒）",
            type="number",
            default=60,
            min_value=1,
            category="basic"
        )
    ],
    "groq_api": [
        ConfigItemSchema(env_var="GROQ_API_KEY", label="API 密钥", description="你的 Groq API 密钥", type="password", required=True, category="credentials"),
        ConfigItemSchema(env_var="GROQ_ENDPOINT", label="端点地址", description="Groq API 端点 (通常不需要修改)", type="text", default="https://api.groq.com/openai/v1", category="endpoint"),
        ConfigItemSchema(env_var="GROQ_DEFAULT_MODEL", label="默认模型", description="默认使用的 Groq 模型 (e.g., llama3-8b-8192)", type="text", default="llama3-8b-8192", category="basic"),
        ConfigItemSchema(env_var="GROQ_TEMPERATURE", label="Temperature", type="number", category="model_params", min_value=0.0, max_value=2.0, step_value=0.1),
        ConfigItemSchema(env_var="GROQ_MAX_TOKENS", label="Max Tokens", type="number", category="model_params", min_value=1, step_value=1),
        ConfigItemSchema(env_var="GROQ_TOP_P", label="Top P", type="number", default=0.9, min_value=0, max_value=1, step_value=0.05, category="model_params"),
    ],
    "together_ai": [
        ConfigItemSchema(env_var="TOGETHER_API_KEY", label="API 密钥", description="你的 Together AI API 密钥", type="password", required=True, category="credentials"),
        ConfigItemSchema(env_var="TOGETHER_ENDPOINT", label="端点地址", description="Together AI API 端点", type="text", default="https://api.together.xyz/v1", category="endpoint"),
        ConfigItemSchema(env_var="TOGETHER_DEFAULT_MODEL", label="默认模型", description="默认使用的 Together AI 模型", type="text", category="basic"),
        ConfigItemSchema(env_var="TOGETHER_TEMPERATURE", label="Temperature", type="number", category="model_params", min_value=0.0, max_value=2.0, step_value=0.1),
        ConfigItemSchema(env_var="TOGETHER_MAX_TOKENS", label="Max Tokens", type="number", category="model_params", min_value=1, step_value=1),
        ConfigItemSchema(env_var="TOGETHER_TOP_P", label="Top P", type="number", default=0.9, min_value=0, max_value=1, step_value=0.05, category="model_params"),
    ],
    "mistral_ai": [
        ConfigItemSchema(env_var="MISTRAL_API_KEY", label="API 密钥", description="你的 Mistral AI API 密钥", type="password", required=True, category="credentials"),
        ConfigItemSchema(env_var="MISTRAL_ENDPOINT", label="端点地址", description="Mistral AI API 端点", type="text", default="https://api.mistral.ai/v1", category="endpoint"),
        ConfigItemSchema(env_var="MISTRAL_DEFAULT_MODEL", label="默认模型", description="默认使用的 Mistral 模型", type="text", default="mistral-tiny", category="basic"),
        ConfigItemSchema(env_var="MISTRAL_TEMPERATURE", label="Temperature", type="number", category="model_params", min_value=0.0, max_value=1.0, step_value=0.1),
        ConfigItemSchema(env_var="MISTRAL_MAX_TOKENS", label="Max Tokens", type="number", category="model_params", min_value=1, step_value=1),
        ConfigItemSchema(env_var="MISTRAL_TOP_P", label="Top P", type="number", default=0.9, min_value=0, max_value=1, step_value=0.05, category="model_params"),
    ],
    "perplexity_ai": [
        ConfigItemSchema(env_var="PERPLEXITY_API_KEY", label="API 密钥", description="你的 Perplexity AI API 密钥", type="password", required=True, category="credentials"),
        ConfigItemSchema(env_var="PERPLEXITY_ENDPOINT", label="端点地址", description="Perplexity API 端点", type="text", default="https://api.perplexity.ai", category="endpoint"),
        ConfigItemSchema(env_var="PERPLEXITY_DEFAULT_MODEL", label="默认模型", description="默认使用的 Perplexity 模型", type="text", default="llama-3-sonar-small-32k-chat", category="basic"),
        ConfigItemSchema(env_var="PERPLEXITY_TEMPERATURE", label="Temperature", type="number", category="model_params", min_value=0.0, max_value=2.0, step_value=0.1),
        ConfigItemSchema(env_var="PERPLEXITY_MAX_TOKENS", label="Max Tokens", type="number", category="model_params", min_value=1, step_value=1),
        ConfigItemSchema(env_var="PERPLEXITY_TOP_P", label="Top P", type="number", default=0.9, min_value=0, max_value=1, step_value=0.05, category="model_params"),
    ],
    "anyscale_endpoints": [
        ConfigItemSchema(env_var="ANYSCALE_API_KEY", label="API 密钥", description="你的 Anyscale Endpoints API 密钥", type="password", required=True, category="credentials"),
        ConfigItemSchema(env_var="ANYSCALE_ENDPOINT", label="端点地址", description="Anyscale API 端点", type="text", default="https://api.endpoints.anyscale.com/v1", category="endpoint"),
        ConfigItemSchema(env_var="ANYSCALE_DEFAULT_MODEL", label="默认模型", description="默认使用的 Anyscale 模型", type="text", default="mistralai/Mistral-7B-Instruct-v0.1", category="basic"),
        ConfigItemSchema(env_var="ANYSCALE_TEMPERATURE", label="Temperature", type="number", category="model_params", min_value=0.0, max_value=2.0, step_value=0.1),
        ConfigItemSchema(env_var="ANYSCALE_MAX_TOKENS", label="Max Tokens", type="number", category="model_params", min_value=1, step_value=1),
        ConfigItemSchema(env_var="ANYSCALE_TOP_P", label="Top P", type="number", default=0.9, min_value=0, max_value=1, step_value=0.05, category="model_params"),
    ],
    "cohere_compatible": [
        ConfigItemSchema(env_var="COHERE_API_KEY", label="API 密钥", description="你的 Cohere API 密钥", type="password", required=True, category="credentials"),
        ConfigItemSchema(env_var="COHERE_ENDPOINT", label="端点地址", description="Cohere API 端点 (OpenAI 兼容)", type="text", default="https://api.cohere.ai/v1", category="endpoint"), # Verify default endpoint
        ConfigItemSchema(env_var="COHERE_DEFAULT_MODEL", label="默认模型", description="默认使用的 Cohere 模型 (e.g., command-r)", type="text", default="command-r", category="basic"),
        ConfigItemSchema(env_var="COHERE_TEMPERATURE", label="Temperature", type="number", category="model_params", min_value=0.0, max_value=1.0, step_value=0.1), # Cohere temp range might differ
        ConfigItemSchema(env_var="COHERE_MAX_TOKENS", label="Max Tokens", type="number", category="model_params", min_value=1, step_value=1),
        ConfigItemSchema(env_var="COHERE_TOP_P", label="Top P", type="number", default=0.9, min_value=0, max_value=1, step_value=0.05, category="model_params"),
        # Cohere might use TOP_K instead or additionally
        ConfigItemSchema(env_var="COHERE_TOP_K", label="Top K", type="number", category="model_params"),
    ],
    "open_router": [
        ConfigItemSchema(env_var="OPEN_ROUTER_API_KEY", label="API 密钥", description="你的 OpenRouter API 密钥", type="password", required=True, category="credentials"),
        ConfigItemSchema(env_var="OPEN_ROUTER_ENDPOINT", label="端点地址", description="OpenRouter API 端点", type="text", default="https://openrouter.ai/api/v1", category="endpoint"),
        ConfigItemSchema(env_var="OPEN_ROUTER_DEFAULT_MODEL", label="默认模型", description="默认使用的 OpenRouter 模型 (需要包含提供商前缀，如 google/gemini-flash-1.5)", type="text", category="basic"),
        ConfigItemSchema(env_var="OPEN_ROUTER_HTTP_REFERER", label="HTTP Referer (可选)", description="你的网站 URL (可选)", type="text", category="basic"),
        ConfigItemSchema(env_var="OPEN_ROUTER_X_TITLE", label="X-Title (可选)", description="你的应用名称 (可选)", type="text", category="basic"),
        ConfigItemSchema(env_var="OPEN_ROUTER_TEMPERATURE", label="Temperature", type="number", category="model_params", min_value=0.0, max_value=2.0, step_value=0.1),
        ConfigItemSchema(env_var="OPEN_ROUTER_MAX_TOKENS", label="Max Tokens", type="number", category="model_params", min_value=1, step_value=1),
        ConfigItemSchema(env_var="OPEN_ROUTER_TOP_P", label="Top P", type="number", default=0.9, min_value=0, max_value=1, step_value=0.05, category="model_params"),
    ],
    "Free_Qwen3": [],
    # Add schemas for other providers here...
}

# --- 自动补全所有 provider 的 REQUEST_TIMEOUT 字段 ---
for provider, items in PROVIDER_SCHEMAS.items():
    # 生成标准 env_var
    env_prefix = provider.upper().replace('-', '_')
    timeout_env = f"{env_prefix}_REQUEST_TIMEOUT"
    # 检查是否已存在
    if not any(item.env_var == timeout_env for item in items):
        items.append(ConfigItemSchema(
            env_var=timeout_env,
            label="请求超时 (秒)",
            description="API 请求的超时时间（秒）",
            type="number",
            default=60,
            min_value=1,
            category="basic"
        ))

# 定义一个通用的 OpenAI 兼容接口的 Schema
# 可以根据需要调整包含的参数
GENERAL_OPENAI_COMPATIBLE_SCHEMA: List[ConfigItemSchema] = [
    ConfigItemSchema(env_var="_API_KEY", label="API 密钥", description="用于访问此 API 的密钥", type="password", required=True, category="credentials"),
    ConfigItemSchema(env_var="_ENDPOINT", label="端点地址", description="API 的基础 URL (例如 https://api.openai.com/v1)", type="text", required=False, category="endpoint"),
    ConfigItemSchema(env_var="_DEFAULT_MODEL", label="默认模型", description="默认使用的模型名称", type="text", required=False, category="basic"),
    ConfigItemSchema(env_var="_TEMPERATURE", label="Temperature", description="控制生成文本的随机性 (0-2)", type="number", default=0.7, min_value=0, max_value=2, step_value=0.1, category="model_params"),
    ConfigItemSchema(env_var="_MAX_TOKENS", label="Max Tokens", description="限制单次响应生成的最大 token 数", type="number", default=2048, min_value=1, step_value=1, category="model_params"),
    ConfigItemSchema(env_var="_TOP_P", label="Top P", description="核采样阈值 (0-1)", type="number", default=0.9, min_value=0, max_value=1, step_value=0.05, category="model_params"),
    # 可以根据需要添加其他通用参数，如 frequency_penalty, presence_penalty
]

# --- 路由 --- 
提供商路由 = APIRouter(tags=["providers"])

# --- Helper Function to Get Dependency (if needed by routes) ---
# This function ensures that the api_manager instance is available if needed
# It should only be used in routes that actually perform save operations or
# need direct access to the manager's state.
def get_api_manager_dependency():
    # Ensure the global api_manager instance is returned
    if api_manager is None:
        日志记录器.critical("API Manager instance is not initialized!")
        raise HTTPException(status_code=500, detail="API Manager not initialized")
    return api_manager

@提供商路由.get("/settings/schema", response_model=SettingsSchemaResponse, summary="获取所有设置项的 Schema 定义")
async def get_settings_schema(): # Removed api_manager dependency here
    """
    生成设置页面的 Schema，包含全局设置和所有提供商的特定设置。
    修改：不再依赖硬编码的 PROVIDER_SCHEMAS。
          为所有提供商生成通用的 Schema (基于 GENERAL_OPENAI_COMPATIBLE_SCHEMA)，
          并尝试用当前 .env 值覆盖默认值。
    """
    日志记录器.info("开始获取设置 Schema (通用逻辑)")
    try:
        # 1. 处理全局设置 Schema
        global_schema_processed = []
        all_provider_meta = get_all_provider_metadata()
        provider_options = [
            SelectOption(label=meta.get('display_name', meta['standard_name']), value=meta['standard_name']) 
            for meta in all_provider_meta
        ]
        # Load current global env vars
        dotenv_path = dotenv.find_dotenv(raise_error_if_not_found=False)
        global_env_vars = {**dotenv.dotenv_values(dotenv_path), **os.environ}
        日志记录器.debug(f"读取到的当前全局环境变量值: { {k:v for k,v in global_env_vars.items() if k in [item.env_var for item in GLOBAL_SCHEMA]} }")

        for item in GLOBAL_SCHEMA:
            processed_item = item.copy(deep=True)
            if item.env_var == "DEFAULT_PROVIDER":
                processed_item.options = provider_options
            
            # Use current env value to override default
            current_value = global_env_vars.get(item.env_var)
            if current_value is not None:
                 # Try to convert to schema type if needed
                 try:
                     if item.type == 'number':
                         current_value = float(current_value) if '.' in current_value else int(current_value)
                     elif item.type == 'boolean':
                         current_value = current_value.lower() == 'true'
                     # Add other type conversions if necessary
                     processed_item.default = current_value
                     日志记录器.debug(f"全局设置 '{item.env_var}' 使用当前值覆盖默认值: {current_value}")
                 except ValueError:
                      日志记录器.warning(f"无法将全局设置 '{item.env_var}' 的值 '{current_value}' 转换为类型 '{item.type}'。保留原始默认值。")
            
            global_schema_processed.append(processed_item)

        # 2. 处理提供商设置 Schema (通用逻辑)
        provider_settings_processed: Dict[str, ProviderSchema] = {}
        for provider_meta in all_provider_meta:
            standard_name = provider_meta["standard_name"]
            display_name = provider_meta.get("display_name", standard_name)
            env_prefix = provider_meta.get("env_prefix", "")
            日志记录器.debug(f"为提供商 '{standard_name}' 生成通用 Schema")
            
            # --- 合并 PROVIDER_SCHEMAS 和通用模板（去重） --- 
            provider_schema_items = copy.deepcopy(PROVIDER_SCHEMAS.get(standard_name, []))
            existing_env_vars = {item.env_var for item in provider_schema_items}
            general_schema_template = copy.deepcopy(GENERAL_OPENAI_COMPATIBLE_SCHEMA)
            for template_item in general_schema_template:
                concrete_env_var = f"{env_prefix}{template_item.env_var[1:]}" 
                template_item.env_var = concrete_env_var
                if concrete_env_var not in existing_env_vars:
                    provider_schema_items.append(template_item)
                    existing_env_vars.add(concrete_env_var)
            # ----------------------------- 

            # --- 尝试获取当前配置以覆盖默认值 --- 
            current_config: Optional[Dict[str, Any]] = None
            try:
                handler = get_handler(standard_name) # Factory handles reading .env based on prefix
                if handler:
                    current_config = handler.config
                    日志记录器.debug(f"成功获取提供商 '{standard_name}' 的当前配置用于 Schema: {list(current_config.keys()) if current_config else 'None'}")
                else:
                     日志记录器.warning(f"无法为提供商 '{standard_name}' 获取处理器实例以填充当前设置值。将使用 Schema 默认值。")
            except Exception as e:
                日志记录器.warning(f"获取提供商 '{standard_name}' 处理器实例时出错 (用于 Schema): {e}。将使用 Schema 默认值。", exc_info=False)

            # --- 使用当前配置覆盖 Schema 默认值 --- 
            processed_schema_items = []
            if current_config:
                for item in provider_schema_items:
                    processed_item = item.copy(deep=True)
                    if item.env_var in current_config:
                        current_value = current_config[item.env_var]
                        if current_value is not None:
                             try:
                                 if item.type == 'number':
                                     current_value = float(current_value) if isinstance(current_value, str) and '.' in current_value else int(current_value)
                                 elif item.type == 'boolean':
                                     current_value = str(current_value).lower() == 'true'
                                 processed_item.default = current_value
                             except (ValueError, TypeError):
                                 日志记录器.warning(f"无法将提供商 '{standard_name}' 设置 '{item.env_var}' 的值 '{current_value}' 转换为类型 '{item.type}'。保留原始默认值。")
                    processed_schema_items.append(processed_item)
            else:
                processed_schema_items = provider_schema_items
            # ------------------------------------
            
            # 创建 ProviderSchema 对象
            provider_settings_processed[standard_name] = ProviderSchema(
                provider_name=standard_name,
                display_name=display_name,
                config_items=processed_schema_items
            )

        # 3. 构建最终响应
        response = SettingsSchemaResponse(
            global_settings=global_schema_processed,
            provider_settings=provider_settings_processed
        )
        日志记录器.info("成功生成设置 Schema 响应 (通用逻辑)")
        return response

    except Exception as e:
        日志记录器.exception(f"生成设置 Schema 时发生意外错误: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error while generating settings schema: {e}")

# --- Save Settings Endpoint ---
@提供商路由.post("/settings/save-all", summary="保存所有设置到 .env 文件")
async def 保存所有设置(
    # Directly receives the dictionary of environment variables to update/remove
    env_vars_to_update: Dict[str, Optional[str]] = Body(...), 
    # Keep dependency here as we use the api_manager instance to save
    api_manager_instance: Any = Depends(get_api_manager_dependency)
):
    """
    Receives a dictionary mapping environment variable names (e.g., 'SILICONFLOW_API_KEY')
    to their desired values (or null/None to unset). Saves these directly to the .env file
    using the APIManager instance.
    The frontend is now responsible for constructing the full env var key names.
    """
    日志记录器.info(f"收到保存设置请求，包含 {len(env_vars_to_update)} 个环境变量更新。")
    日志记录器.debug(f"待更新环境变量: {env_vars_to_update}") # Be careful logging potentially sensitive keys

    try:
        # Use the injected api_manager instance to save settings
        success, message = api_manager_instance.save_settings_to_env(env_vars_to_update)
        if success:
            日志记录器.info(f"设置成功保存: {message}")
            # NOTE: No need to call reload_configs on api_manager anymore.
            # Factory reads .env in real-time.
            return JSONResponse(content={"status": "success", "message": message})
        else:
            日志记录器.error(f"保存设置失败: {message}")
            raise HTTPException(status_code=500, detail=message)
    except Exception as e:
        日志记录器.exception(f"保存设置时发生意外错误: {e}")
        raise HTTPException(status_code=500, detail=f"保存设置时发生意外错误: {e}")


# --- Provider List Endpoint ---
@提供商路由.get("/providers", summary="获取可用的API提供商列表")
async def 获取提供商列表(): # No dependency needed
    """
    获取所有在 providers_meta.json 中定义的，且已在 .env 文件中正确配置的 API 提供商列表。
    返回前端所需的格式，包含名称、显示名称和可选的图标。
    """
    日志记录器.info("开始获取已配置的 API 提供商列表。")
    configured_providers = []
    try:
        all_metadata = get_all_provider_metadata()
        日志记录器.debug(f"获取到 {len(all_metadata)} 条元数据，开始检查配置状态。")
        
        for meta in all_metadata:
            standard_name = meta.get('standard_name')
            if not standard_name:
                日志记录器.warning(f"元数据条目缺少 standard_name: {meta}")
                continue
            
            # 使用 api_manager 检查配置状态
            is_configured, status_message = api_manager.is_provider_configured(standard_name)
            日志记录器.debug(f"提供商 '{standard_name}' 配置检查结果: {is_configured}, 消息: {status_message}")
            
            if is_configured:
                provider_info = {
                    "name": standard_name,
                    "display_name": meta.get('display_name', standard_name),
                    # 将来可以从元数据添加图标信息
                    # "icon": meta.get('icon')
                }
                configured_providers.append(provider_info)
                日志记录器.debug(f"添加已配置的提供商: {provider_info}")
            else:
                 日志记录器.debug(f"跳过未配置的提供商: {standard_name}")

        日志记录器.info(f"返回 {len(configured_providers)} 个已配置的提供商。")
        return configured_providers
    except Exception as e:
        日志记录器.error(f"获取已配置提供商列表时出错: {e}", exc_info=True)
        # 返回空列表或抛出 HTTP 异常，取决于需求
        raise HTTPException(status_code=500, detail=f"获取提供商列表时发生内部错误: {str(e)}")

# --- Get Global Settings Endpoint ---
@提供商路由.get("/settings/global", summary="获取全局设置")
async def 获取全局设置(): # No dependency needed
    """
    Reads global settings directly from environment variables.
    """
    日志记录器.info("获取全局设置 (直接从环境变量读取)")
    try:
        # Define the global settings keys to look for in the environment
        global_keys = ["DEFAULT_PROVIDER"] # Add other global keys if needed

        # Load .env to ensure os.environ reflects the latest values for this request
        # Use find_dotenv to locate the file robustly
        dotenv_path = dotenv.find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=True)
        if dotenv_path and os.path.exists(dotenv_path):
             loaded = dotenv.load_dotenv(dotenv_path=dotenv_path, override=True)
             日志记录器.debug(f"Reloaded .env for global settings from {dotenv_path}: {loaded}")
        else:
             日志记录器.warning(f"Could not find .env to reload for global settings (path: {dotenv_path}). Using current environment state.")

        # Read the defined global settings from the environment
        global_settings = {key: os.environ.get(key) for key in global_keys}

        # Filter out settings that were not found (value is None)
        # global_settings = {k: v for k, v in global_settings.items() if v is not None}

        日志记录器.info(f"读取到的全局设置: {global_settings}")
        return global_settings
    except Exception as e:
        日志记录器.exception(f"获取全局设置时出错: {e}")
        raise HTTPException(status_code=500, detail=f"获取全局设置时出错: {e}")

# --- Get Provider Settings Endpoint (Robust Env Reading) ---
@提供商路由.get("/settings/providers", summary="获取提供商运行时配置")
async def 获取提供商设置(): 
    """
    Reads provider-specific settings directly from environment variables based on prefix.
    Metadata is read directly from config/providers_meta.json on each request.
    Returns a dictionary mapping provider standard names to their current settings values read from .env.
    Sensitive values like API keys are masked based on naming convention or schema if available.
    """
    日志记录器.info("获取所有提供商设置 (实时读取元数据, 基于前缀读取环境变量)")
    provider_settings_response = {}
    all_providers_meta = []
    meta_path = None

    # 1. Read providers_meta.json directly
    meta_path = None # Initialize for logging
    try:
        # Calculate path directly using pathlib
        _current_file_path = Path(__file__).resolve()
        # Go up 4 levels: src/api/routes -> src/api -> src -> project_root
        _project_root_calculated = _current_file_path.parent.parent.parent.parent 
        meta_path = _project_root_calculated / "config" / "providers_meta.json"
        日志记录器.debug(f"Correctly calculated metadata file path as Path object: {meta_path}")

        if meta_path.exists():
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata_from_file = json.load(f)
                if isinstance(metadata_from_file, list):
                    all_providers_meta = metadata_from_file
                    日志记录器.debug(f"成功从 {meta_path} 读取 {len(all_providers_meta)} 条元数据。")
                else:
                    日志记录器.error(f"元数据文件 {meta_path} 格式无效，期望列表。")
                    return {}
        else:
            日志记录器.warning(f"元数据文件 {meta_path} 不存在。无法获取提供商设置。")
            return {}
    except json.JSONDecodeError as json_err:
        log_path_str = str(meta_path) if meta_path else "未知路径"
        日志记录器.error(f"解析元数据文件 {log_path_str} 失败: {json_err}")
        raise HTTPException(status_code=500, detail="元数据文件格式错误")
    except Exception as read_err:
        log_path_str = str(meta_path) if meta_path else "未知路径"
        日志记录器.error(f"读取元数据文件 {log_path_str} 时出错: {read_err}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"无法读取元数据文件: {read_err}")

    # 2. Reload .env and process providers based on prefix
    try:
        dotenv_path = dotenv.find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=True)
        if dotenv_path and os.path.exists(dotenv_path):
             loaded = dotenv.load_dotenv(dotenv_path=dotenv_path, override=True)
             日志记录器.debug(f"Reloaded .env for provider settings from {dotenv_path}: {loaded}")
        else:
             日志记录器.warning(f"Could not find .env to reload for provider settings (path: {dotenv_path}). Using current environment state.")

        # Get a snapshot of current environment variables AFTER reloading .env
        current_env = os.environ.copy()

        if not all_providers_meta:
            日志记录器.warning("元数据列表为空，无法读取提供商设置。")
            return {}

        for meta in all_providers_meta:
            # --- Add Log to track loop --- 
            current_processing_name = meta.get('standard_name', '[Missing standard_name]')
            日志记录器.debug(f"--- Processing metadata entry for: {current_processing_name} ---")
            # -----------------------------
            if not isinstance(meta, dict) or 'standard_name' not in meta or 'env_prefix' not in meta:
                 日志记录器.warning(f"跳过无效或缺少 env_prefix 的元数据条目: {meta}")
                 continue
                 
            standard_name = meta['standard_name']
            display_name = meta.get('display_name', standard_name)
            env_prefix = meta['env_prefix']
            
            # Initialize config dict for this provider
            current_provider_config = {"provider_name": standard_name, "display_name": display_name}
            
            # Get schema if available (for masking hints)
            schema_items = PROVIDER_SCHEMAS.get(standard_name, [])
            sensitive_keys_from_schema = {item.env_var for item in schema_items if hasattr(item, 'type') and item.type == 'password'}

            # Iterate through current environment variables to find matching prefix
            matched_keys = [] # For debugging
            for env_key, value in current_env.items():
                # --- Case-insensitive prefix check --- 
                if env_key.upper().startswith(env_prefix.upper()): 
                    matched_keys.append(env_key) # Log matched keys
                    config_key = env_key 
                    
                    # Masking logic based on schema or naming convention
                    is_sensitive = ('API_KEY' in env_key.upper() or 
                                    'SECRET' in env_key.upper() or 
                                    env_key in sensitive_keys_from_schema)
                    
                    if is_sensitive:
                         # --- Masking Logic (copied) ---
                        is_volc_key = standard_name == "volc_engine" and 'API_KEY' in env_key.upper()
                        if is_volc_key and ';' in value:
                            parts = value.split(';', 1)
                            ak_masked = parts[0][:4] + "..." if len(parts[0]) > 4 else "***"
                            sk_masked = parts[1][:4] + "..." if len(parts) > 1 and len(parts[1]) > 4 else "***"
                            current_provider_config[config_key] = f"{ak_masked};{sk_masked}"
                        elif len(value) > 8:
                            current_provider_config[config_key] = value[:4] + "..." + value[-4:]
                        else: 
                            current_provider_config[config_key] = "***"
                        # --- End Masking Logic ---
                    else:
                        current_provider_config[config_key] = value
            
            # --- Add Debug Log --- 
            日志记录器.debug(f"Provider '{standard_name}' (Prefix: '{env_prefix}'): Found {len(matched_keys)} matching env vars: {matched_keys}")
            # -------------------

            # Add the collected settings for this provider
            # Only add if some settings were actually found (more than just name/display)
            if len(current_provider_config) > 2:
                provider_settings_response[standard_name] = current_provider_config
                日志记录器.debug(f"为 '{standard_name}' 收集到 {len(current_provider_config)-2} 个基于前缀的环境变量配置。")
            else:
                # If only name and display name, maybe still include it?
                # Let's include it so the provider appears in the list, even if unconfigured in .env
                provider_settings_response[standard_name] = current_provider_config
                日志记录器.debug(f"提供商 '{standard_name}' 在 .env 中未找到基于前缀 '{env_prefix}' 的配置。")

        日志记录器.info(f"成功获取 {len(provider_settings_response)} 个提供商的设置 (基于前缀读取环境变量)")
        return provider_settings_response
        
    except Exception as e:
        日志记录器.exception(f"获取提供商设置时出错: {e}")
        raise HTTPException(status_code=500, detail=f"获取提供商设置时出错: {e}")


# --- Get Models Endpoint ---
@提供商路由.get("/models/{provider_name}", summary="获取指定提供商的可用模型列表")
async def 获取模型列表(provider_name: str): # No dependency needed
    """
    Retrieves a list of available models for the specified provider.
    Handles error cases and includes caching for performance.
    """
    # 安全初始化变量，防止未定义错误
    model = "unknown"  # 默认值
    provider = "unknown"  # 默认值
    start_time = None  # 初始化为None

    # 记录请求开始时间用于性能监控
    start_time = asyncio.get_event_loop().time()
    
    日志记录器.info(f"收到获取模型列表请求: Provider='{provider_name}'")
    
    # 初始化响应数据
    response_data = {
        "provider": provider_name,
        "models": [],
        "status": "ok",
        "message": "",
        "error_details": None,
        "latency_ms": None
    }

    standard_provider = "" # 初始化变量处理可能的错误
    try:
        # 首先标准化提供商名称，一致处理别名
        standard_provider = standardize_provider_name(provider_name)
        日志记录器.debug(f"提供商名称标准化: '{provider_name}' -> '{standard_provider}'")
    except ValueError as e:
        # 如果标准化失败（未知提供商），返回404
        error_msg = f"获取模型列表失败: {e}"
        日志记录器.warning(error_msg)
        response_data["status"] = "error"
        response_data["message"] = str(e)
        return JSONResponse(content=response_data, status_code=404)

    # 使用标准名称作为缓存键
    cache_key = f"models_{standard_provider}"

    # --- 尝试从缓存获取 ---
    try:
        日志记录器.debug(f"尝试从缓存获取模型列表: key='{cache_key}'")
        cached_data = 缓存管理器.get(cache_key)
        if cached_data is not None and isinstance(cached_data, dict) and 'models' in cached_data:
            # 确保缓存项是列表
            if isinstance(cached_data['models'], list):
                日志记录器.info(f"缓存命中：提供商 '{standard_provider}' 的模型列表")
                # 计算延迟
                end_time = asyncio.get_event_loop().time()
                latency = (end_time - start_time) * 1000
                response_data["models"] = cached_data['models']
                response_data["message"] = "从缓存获取模型列表成功"
                response_data["latency_ms"] = round(latency, 2)
                return JSONResponse(content=response_data)
            else:
                日志记录器.warning(f"缓存数据格式无效 (key='{cache_key}'): 预期列表但获得 {type(cached_data['models'])}。忽略缓存。")
                缓存管理器.delete(cache_key) # 删除无效的缓存条目
        elif cached_data is not None:
            日志记录器.warning(f"缓存数据格式无效 (key='{cache_key}'): 预期字典但获得 {type(cached_data)}。忽略缓存。")
            缓存管理器.delete(cache_key) # 删除无效的缓存条目
    except Exception as cache_err:
        # 记录缓存错误但继续从API获取
        日志记录器.error(f"获取缓存时出错 (key='{cache_key}'): {cache_err}", exc_info=True)

    # --- 从提供商API获取数据 ---
    日志记录器.info(f"缓存未命中或无效，尝试从API获取模型列表: Provider='{standard_provider}'")
    
    # 特殊处理Ollama，检查其配置和连接状态
    if standard_provider == "ollama_local":
        try:
            # 直接从.env获取Ollama端点配置
            dotenv_path = dotenv.find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=True)
            日志记录器.debug(f"读取Ollama配置从.env文件: {dotenv_path}")
            env_values = {}
            
            if dotenv_path:
                env_values = dotenv.dotenv_values(dotenv_path)
                日志记录器.debug(f"读取到Ollama配置数量: {len(env_values)} 个键值对")
            
            # 获取Ollama端点配置，检查更多可能的键
            endpoint = (env_values.get("OLLAMA_ENDPOINT") or 
                       env_values.get("OLLAMA_BASE_URL") or 
                       env_values.get("OLLAMA_API_BASE_URL"))
            
            if not endpoint:
                日志记录器.warning("Ollama端点配置缺失：OLLAMA_ENDPOINT/OLLAMA_BASE_URL/OLLAMA_API_BASE_URL均未设置")
                # 使用默认值
                endpoint = "http://localhost:11434"
                日志记录器.info(f"使用默认Ollama端点: {endpoint}")
            else:
                日志记录器.info(f"从.env获取到Ollama端点: {endpoint}")
                
            # 直接尝试从Ollama获取模型列表
            # 确保端点没有多余的斜杠
            if endpoint.endswith('/'):
                endpoint = endpoint.rstrip('/')
                
            list_endpoint = f"{endpoint}/api/tags"
            日志记录器.info(f"尝试直接从Ollama获取模型列表: {list_endpoint}")
            
            async with aiohttp.ClientSession() as session:
                try:
                    # 添加错误处理和超时设置
                    日志记录器.debug("正在发送API请求到Ollama...")
                    
                    headers = {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    }
                    
                    async with session.get(
                        list_endpoint, 
                        timeout=aiohttp.ClientTimeout(total=10),
                        headers=headers
                    ) as resp:
                        日志记录器.debug(f"收到Ollama API响应: 状态码 {resp.status}")
                        
                        if resp.status != 200:
                            error_text = await resp.text()
                            日志记录器.error(f"Ollama API返回非200状态码: {resp.status}, {error_text}")
                            response_data["status"] = "error"
                            response_data["message"] = f"Ollama API返回错误: HTTP {resp.status}"
                            response_data["error_details"] = error_text
                            return JSONResponse(content=response_data, status_code=resp.status)
                        
                        # 解析JSON响应
                        try:
                            data = await resp.json()
                            日志记录器.debug(f"Ollama API数据结构: {data.keys() if isinstance(data, dict) else '不是字典'}")
                            
                            if "models" in data and isinstance(data["models"], list):
                                # 这是正确的Ollama API响应格式
                                ollama_models = data["models"]
                                日志记录器.debug(f"收到原始模型数据: {len(ollama_models)} 个模型")
                                
                                models_list = [
                                    {"id": model.get("name", "unknown"), 
                                     "name": model.get("name", "unknown"),
                                     "provider": "ollama_local"
                                    } 
                                    for model in ollama_models 
                                    if "name" in model
                                ]
                                
                                日志记录器.info(f"成功从Ollama直接获取模型列表，共 {len(models_list)} 个模型")
                                
                                # 缓存结果
                                缓存管理器.set({'models': models_list}, cache_key)
                                
                                # 成功返回
                                end_time = asyncio.get_event_loop().time()
                                latency = (end_time - start_time) * 1000
                                response_data["models"] = models_list
                                response_data["message"] = f"成功从Ollama直接获取模型列表，共 {len(models_list)} 个模型"
                                response_data["latency_ms"] = round(latency, 2)
                                return JSONResponse(content=response_data)
                            else:
                                日志记录器.warning(f"Ollama API返回格式未知: {data}")
                                # 继续使用常规处理器获取模型
                        except json.JSONDecodeError as je:
                            日志记录器.error(f"解析Ollama API响应时出错: {je}")
                            response_data["status"] = "error"
                            response_data["message"] = "无法解析Ollama API响应"
                            response_data["error_details"] = str(je)
                            return JSONResponse(content=response_data, status_code=500)
                except aiohttp.ClientError as e:
                    日志记录器.error(f"直接连接Ollama API失败: {e}")
                    response_data["status"] = "error"
                    response_data["message"] = f"无法连接到Ollama API: {e}"
                    response_data["error_details"] = str(e)
                    return JSONResponse(content=response_data, status_code=500)
        except Exception as e:
            日志记录器.error(f"直接获取Ollama模型列表出错: {e}", exc_info=True)
            response_data["status"] = "error"
            response_data["message"] = f"获取Ollama模型列表时出错: {e}"
            response_data["error_details"] = str(e)
            return JSONResponse(content=response_data, status_code=500)
    
    # 加载最新的.env配置
    try:
        # 确保我们从.env加载最新配置
        dotenv_path = dotenv.find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=True)
        if dotenv_path:
            dotenv.load_dotenv(dotenv_path=dotenv_path, override=True)
            日志记录器.debug(f"已从.env加载最新配置: {dotenv_path}")
    except Exception as env_load_err:
        日志记录器.error(f"加载.env配置时出错: {env_load_err}", exc_info=True)
        # 继续处理，使用当前环境变量
    
    try:
        # 获取处理器实例（从.env读取最新配置）
        日志记录器.debug(f"创建处理器实例: Provider='{standard_provider}'")
        handler = get_handler(standard_provider) # 使用标准名称

        if hasattr(handler, 'get_available_models'):
            日志记录器.debug(f"调用 {standard_provider} 的 get_available_models 方法")
            models = []
            
            # 确保方法是可等待的（异步）
            if asyncio.iscoroutinefunction(handler.get_available_models):
                # 使用asyncio.wait_for添加超时
                try:
                    # 增加超时时间以便处理慢速连接
                    timeout_seconds = 30.0  # 30秒超时
                    日志记录器.debug(f"使用 {timeout_seconds}秒 超时调用异步 get_available_models")
                    models = await asyncio.wait_for(handler.get_available_models(), timeout=timeout_seconds)
                except asyncio.TimeoutError:
                    error_msg = f"获取模型列表超时 ({timeout_seconds}秒): Provider='{standard_provider}'"
                    日志记录器.error(error_msg)
                    response_data["status"] = "error"
                    response_data["message"] = "获取模型列表超时"
                    response_data["error_details"] = f"操作超过 {timeout_seconds} 秒未完成"
                    return JSONResponse(content=response_data, status_code=504)
                except Exception as async_err:
                    error_msg = f"调用 {standard_provider}.get_available_models 异步方法时出错: {async_err}"
                    日志记录器.error(error_msg, exc_info=True)
                    # 使用统一的错误处理返回
                    response_data["status"] = "error"
                    response_data["message"] = "获取模型列表失败"
                    response_data["error_details"] = str(async_err)
                    return JSONResponse(content=response_data, status_code=500)
            else:
                # 处理同步方法（不太常见）
                try:
                    日志记录器.debug(f"调用同步 get_available_models 方法")
                    models = handler.get_available_models() # 同步调用没有超时处理
                except Exception as sync_err:
                    error_msg = f"调用 {standard_provider}.get_available_models 同步方法时出错: {sync_err}"
                    日志记录器.error(error_msg, exc_info=True)
                    # 使用统一的错误处理返回
                    response_data["status"] = "error"
                    response_data["message"] = "获取模型列表失败"
                    response_data["error_details"] = str(sync_err)
                    return JSONResponse(content=response_data, status_code=500)

            # 验证响应类型
            if not isinstance(models, list):
                error_msg = f"提供商 '{standard_provider}' get_available_models 返回了非列表类型: {type(models)}"
                日志记录器.error(error_msg)
                response_data["status"] = "error"
                response_data["message"] = "提供商返回了无效的模型列表格式"
                response_data["error_details"] = f"预期返回列表，但获得了 {type(models)}"
                return JSONResponse(content=response_data, status_code=500)

            # 成功获取模型列表
            日志记录器.info(f"成功获取到 {len(models)} 个模型: Provider='{standard_provider}'")
            if len(models) > 0:
                日志记录器.debug(f"模型列表 for {standard_provider}: {models}")
            else:
                日志记录器.warning(f"提供商 '{standard_provider}' 返回了空模型列表")

            # 缓存结果
            try:
                缓存管理器.set({'models': models}, cache_key) # 存储为带 'models' 键的字典
                日志记录器.info(f"模型列表已为 '{standard_provider}' 缓存 (key: {cache_key})")
            except Exception as cache_set_err:
                日志记录器.error(f"缓存模型列表时出错 (key='{cache_key}'): {cache_set_err}", exc_info=True)
                # 如果缓存出错继续处理，不影响返回

            # 计算延迟
            end_time = asyncio.get_event_loop().time()
            latency = (end_time - start_time) * 1000
            
            # 构建成功响应
            response_data["models"] = models
            response_data["message"] = f"成功获取模型列表，共 {len(models)} 个模型"
            response_data["latency_ms"] = round(latency, 2)
            return JSONResponse(content=response_data)
        else:
            error_msg = f"提供商 '{standard_provider}' 的 Handler 没有实现 get_available_models 方法"
            日志记录器.warning(error_msg)
            response_data["status"] = "error"
            response_data["message"] = "该提供商不支持获取模型列表"
            response_data["error_details"] = f"提供商 '{standard_provider}' 未实现获取模型列表功能"
            return JSONResponse(content=response_data, status_code=404)

    except ValueError as ve: # 捕获get_handler错误（如配置加载失败，未知提供商）
        error_msg = f"获取模型列表时，创建或查找 Handler '{standard_provider}' 出错: {ve}"
        日志记录器.error(error_msg, exc_info=True)
        # 如果standardize_provider_name之前失败，standard_provider可能为空
        provider_name_for_error = provider if not standard_provider else standard_provider
        response_data["status"] = "error"
        response_data["message"] = f"提供商 '{provider_name_for_error}' 配置出错"
        response_data["error_details"] = str(ve)
        # 对于配置错误而非服务器错误，返回400
        return JSONResponse(content=response_data, status_code=400)
    except Exception as e: # 处理未预期的错误
        error_msg = f"获取模型列表时发生未捕获异常: {e}"
        日志记录器.error(error_msg, exc_info=True)
        response_data["status"] = "error"
        response_data["message"] = "获取模型列表时发生错误"
        response_data["error_details"] = str(e)
        return JSONResponse(content=response_data, status_code=500)


# --- Provider Status Endpoint ---
@提供商路由.get("/provider-status/{provider_name}", summary="获取指定提供商的状态信息")
async def 获取提供商状态(provider_name: str): # No dependency needed
    """
    Checks the status of a provider.
    Attempts to instantiate the handler (which reads .env).
    Success implies basic configuration might be present.
    Includes a specific online check for Ollama.
    """
    # 安全初始化变量，防止未定义错误
    model = "unknown"  # 默认值
    provider = "unknown"  # 默认值
    start_time = None  # 初始化为None

    日志记录器.info(f"获取提供商状态: {provider_name}")
    status = "error" # Default status
    message = "未知错误"
    standard_name = "" # Initialize
    ollama_endpoint = None

    try:
        # 1. Standardize name first
        standard_name = standardize_provider_name(provider_name)

        # 2. Attempt to get the handler. This implicitly checks:
        #    - Provider is known (metadata exists)
        #    - Handler class can be imported
        #    - Basic .env config reading works
        #    - Handler __init__ succeeds
        日志记录器.info(f"尝试创建提供商 '{standard_name}' 的处理器实例，从 .env 读取最新配置")
        
        # 读取.env文件以确保获取最新的配置
        dotenv_path = dotenv.find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=True)
        if dotenv_path:
            dotenv.load_dotenv(dotenv_path=dotenv_path, override=True)
            日志记录器.debug(f"已从路径读取最新的.env文件: {dotenv_path}")
        
        # 对于Ollama，尝试直接读取endpoint配置
        if standard_name == "ollama_local":
            ollama_endpoint = os.environ.get("OLLAMA_ENDPOINT") or os.environ.get("OLLAMA_BASE_URL")
            if not ollama_endpoint:
                ollama_endpoint = "http://localhost:11434"  # 使用默认值
                日志记录器.info(f"未找到Ollama端点配置，使用默认值: {ollama_endpoint}")
        
        handler = get_handler(standard_name)  # 尝试获取处理器实例
        if handler:
            日志记录器.info(f"Provider '{standard_name}' Handler instantiated successfully. Basic config likely present.")
            status = "ok"  # Initial status if handler creation succeeds
            message = "基本配置有效且 Handler 实例化成功。"
        else:
            status = "error"
            message = "无法创建处理器实例，请检查配置"
            日志记录器.warning(f"无法为提供商 '{standard_name}' 创建处理器实例")
            return {"provider": standard_name, "status": status, "message": message}

        # --- 3. Specific check for Ollama ---
        if standard_name == "ollama_local":
            日志记录器.debug("为 Ollama 执行额外的在线检查")
            # Ensure we have the endpoint
            if not ollama_endpoint:
                ollama_endpoint = handler.endpoint if hasattr(handler, 'endpoint') else "http://localhost:11434"
                日志记录器.debug(f"从处理器获取Ollama端点: {ollama_endpoint}")
            
            # 使用处理器的内置方法检查服务状态
            try:
                # 直接使用handler的check_service_status方法
                if hasattr(handler, 'check_service_status'):
                    status_result = await handler.check_service_status()
                    if status_result["status"] == "available":
                        status = "ok"
                        message = f"Ollama服务在线且可访问：{status_result.get('message', '')}"
                    else:
                        status = "error"
                        message = status_result.get('message', "Ollama服务不可用")
                    
                    日志记录器.info(f"Ollama服务状态检查结果: {status} - {message}")
                    return {"provider": standard_name, "status": status, "message": message}
                
                # 备选方案：使用handler的get_available_models方法
                if hasattr(handler, 'get_available_models'):
                    models = await handler.get_available_models()
                    if models and len(models) > 0:
                        status = "ok"
                        message = f"Ollama服务在线且可访问，发现 {len(models)} 个模型"
                    else:
                        status = "warning"
                        message = "Ollama服务可能在线，但未发现任何模型"
                    
                    日志记录器.info(f"Ollama模型列表检查结果: {status} - {message}")
                    return {"provider": standard_name, "status": status, "message": message}
                
                # 如果前两种方法都不可用，回退到aiohttp直接检查
                日志记录器.debug("回退到直接HTTP检查Ollama状态")
                
                # 定义检查函数
                async def check_ollama_direct(endpoint_url):
                    try:
                        async with aiohttp.ClientSession() as session:
                            # Use a short timeout
                            # Check /api/tags or just / for basic reachability
                            check_url = f"{endpoint_url.rstrip('/')}/api/tags" # More reliable than root
                            日志记录器.debug(f"正在检查Ollama可达性: {check_url}")
                            async with session.get(check_url, timeout=3.0) as response:
                                if response.status == 200:
                                    try:
                                        # 尝试解析响应以验证内容
                                        data = await response.json()
                                        if 'models' in data:
                                            models_count = len(data['models'])
                                            日志记录器.info(f"Ollama服务在 {endpoint_url} 检测活跃，找到 {models_count} 个模型")
                                            return True, f"Ollama服务在线且可访问，发现 {models_count} 个模型。"
                                        else:
                                            日志记录器.info(f"Ollama服务在 {endpoint_url} 检测活跃，但未找到模型列表")
                                            return True, "Ollama服务在线且可访问，但未找到模型列表。"
                                    except Exception as json_err:
                                        日志记录器.warning(f"Ollama响应解析失败: {json_err}")
                                        return True, "Ollama服务在线但响应格式异常。"
                                else:
                                    日志记录器.warning(f"Ollama服务在 {endpoint_url} 响应状态 {response.status} (GET {check_url})")
                                    return False, f"Ollama服务响应异常 (状态: {response.status})。"
                    except asyncio.TimeoutError:
                        日志记录器.warning(f"连接Ollama服务 {endpoint_url} 超时")
                        return False, "连接Ollama服务超时。请确认Ollama服务已启动并监听正确端口。"
                    except aiohttp.ClientConnectorError as conn_err:
                        日志记录器.warning(f"无法连接到Ollama服务 {endpoint_url}: {conn_err}")
                        return False, f"无法连接到Ollama服务地址 ({conn_err})。请检查Ollama是否运行及端口配置是否正确。"
                    except Exception as e:
                        日志记录器.error(f"检查Ollama服务 {endpoint_url} 时发生未知错误: {e}", exc_info=True)
                        return False, f"检查Ollama服务时出错: {e}"
                
                # 运行检查（不需要nest_asyncio，因为我们在异步函数中运行）
                is_running, running_message = await check_ollama_direct(ollama_endpoint)
                
                # 更新状态和消息
                if is_running:
                    status = "ok" # Confirm status is ok
                    message = running_message
                else:
                    status = "error" # Service configured but not reachable/responding correctly
                    message = running_message
            except ImportError as ie:
                日志记录器.warning(f"所需模块未安装，无法执行Ollama在线检查: {ie}")
                status = "warning" # Status is uncertain
                message += f" (无法执行在线检查，缺少必要模块: {ie})"
            except Exception as e:
                日志记录器.error(f"Ollama状态检查时发生意外错误: {e}", exc_info=True)
                status = "error"
                message = "无法检查Ollama状态"
        # --- End Ollama Specific Check ---

        # For other providers, successful handler instantiation is the main check for now.
        # TODO: Implement specific connection tests for other providers if desired.

        return {"provider": standard_name, "status": status, "message": message}

    except ValueError as ve: # Catch errors from get_handler or standardize_provider_name
        日志记录器.warning(f"获取提供商 '{provider_name}' 状态失败: {ve}")
        # If standardization failed, standard_name might be empty
        provider_key = standard_name if standard_name else provider_name
        return {"provider": provider_key, "status": "error", "message": str(ve)}
    except FileNotFoundError as fnf_err: # Catch if metadata or .env is missing critically
        日志记录器.error(f"获取提供商 '{provider_name}' 状态失败 (文件未找到): {fnf_err}")
        provider_key = standard_name if standard_name else provider_name
        return {"provider": provider_key, "status": "error", "message": f"配置错误: {fnf_err}"}
    except Exception as e:
        日志记录器.exception(f"获取提供商 '{provider_name}' 状态时发生意外错误: {e}")
        provider_key = standard_name if standard_name else provider_name
        return {"provider": provider_key, "status": "error", "message": f"检查状态时发生意外错误: {e}"}


# --- Debug Endpoint ---
@提供商路由.get("/debug-env", summary="调试环境变量和配置")
async def 调试环境变量():
    """
     Debug endpoint: Returns environment variables relevant to configured providers.
     Sensitive values are masked.
    """
    日志记录器.info("请求调试环境变量信息")
    try:
        # Find and reload .env to ensure os.environ is fresh for this request
        dotenv_path = dotenv.find_dotenv(filename='.env', raise_error_if_not_found=False, usecwd=True)
        env_file_status = "Not Found"
        if dotenv_path and os.path.exists(dotenv_path):
            dotenv.load_dotenv(dotenv_path=dotenv_path, override=True)
            日志记录器.debug(f"Reloaded .env from: {dotenv_path}")
            env_file_status = dotenv_path
        else:
            日志记录器.warning(f"Could not find .env file for debug endpoint (path: {dotenv_path}). Showing system environment.")

        # Get all relevant environment variables based on provider metadata
        debug_info = {"env_file_path": env_file_status, "providers": {}}
        all_providers_meta = get_all_provider_metadata() # Use factory helper

        for meta in all_providers_meta:
            provider_name = meta['standard_name']
            env_prefix = meta['env_prefix']
            provider_env = {}
            # Define keys to check based on schema + common keys
            schema_items = PROVIDER_SCHEMAS.get(provider_name, [])
            keys_to_check = set(item.env_var for item in schema_items)
            # Add common keys just in case they are not in schema
            keys_to_check.update([
                f"{env_prefix}API_KEY", f"{env_prefix}ENDPOINT", f"{env_prefix}DEFAULT_MODEL",
                f"{env_prefix}TEMPERATURE", f"{env_prefix}MAX_TOKENS", f"{env_prefix}TOP_P",
                f"{env_prefix}REQUEST_TIMEOUT", f"{env_prefix}API_SECRET", f"{env_prefix}ACCESS_KEY",
                f"{env_prefix}SECRET_KEY", f"{env_prefix}API_VERSION", f"{env_prefix}HTTP_REFERER",
                f"{env_prefix}X_TITLE"
            ])
            if provider_name == "google_gemini": keys_to_check.add("GOOGLE_APPLICATION_CREDENTIALS")

            # Read values from os.environ
            for key in sorted(list(keys_to_check)): # Sort for consistent output
                value = os.environ.get(key)
                if value is not None:
                    # Mask sensitive values
                    # Check based on key naming convention or schema type (if available)
                    is_sensitive = ('KEY' in key.upper() or 'SECRET' in key.upper() or
                                    any(item.env_var == key and item.type == 'password' for item in schema_items))

                    if is_sensitive:
                        is_volc_key = provider_name == "volc_engine" and 'API_KEY' in key.upper()
                        if is_volc_key and ';' in value:
                            parts = value.split(';', 1)
                            ak_masked = parts[0][:4] + "..." if len(parts[0]) > 4 else "***"
                            sk_masked = parts[1][:4] + "..." if len(parts) > 1 and len(parts[1]) > 4 else "***"
                            provider_env[key] = f"{ak_masked};{sk_masked}"
                        elif len(value) > 8:
                            provider_env[key] = value[:4] + "..." + value[-4:]
                        else: # Short sensitive value
                            provider_env[key] = "***"
                    else:
                        provider_env[key] = value

            # Only include provider if some relevant env vars were found
            if provider_env:
                debug_info["providers"][provider_name] = provider_env

        # Add global vars
        debug_info["global"] = {
           "DEFAULT_PROVIDER": os.environ.get("DEFAULT_PROVIDER")
        }

        日志记录器.info("成功收集调试环境信息")
        return debug_info

    except Exception as e:
        日志记录器.exception(f"获取调试环境信息时出错: {e}")
        raise HTTPException(status_code=500, detail=f"获取调试环境信息时出错: {e}")


# --- Test Model Endpoint ---
@提供商路由.post("/provider/test-model", summary="测试模型连接")
async def 测试模型连接(
    request: TestModelRequest = Body(...)
):
    """
    测试指定提供商和模型的连接性
    """
    std_provider_name = standardize_provider_name(request.provider)
    if not std_provider_name:
        raise HTTPException(status_code=400, detail=f"未知的提供商别名: {request.provider}")

    日志记录器.info(f"收到模型测试请求: Provider='{std_provider_name}', Model='{request.model}'")

    try:
        # 注意：这里我们总是获取最新的配置来测试
        # 移除 model 参数，get_handler 不接受它
        # 修正：使用位置参数调用 get_handler
        handler = get_handler(std_provider_name) 
        if not handler:
             # 如果 get_handler 返回 None，说明配置不完整或提供商不受支持
             日志记录器.error(f"无法为 '{std_provider_name}' 获取处理器实例，可能配置不完整或不支持。")
             # 修正：返回 JSONResponse 而不是抛出 HTTPException
             return JSONResponse(
                 status_code=400, # Bad Request due to config issue
                 content={"status": "error", "message": f"无法为提供商 '{std_provider_name}' 获取处理器实例，请检查配置。"}
             )

        # 将 model 参数传递给 test_connection 方法
        result = await handler.test_connection(model=request.model)

        # --- 新增修改开始 ---
        # 如果基础测试成功，但消息不是预期的简单字符串（可能包含复杂结构或错误提示），
        # 则覆盖为标准成功消息，避免在前端显示内部细节。
        if result.get("status") == "success":
             # 保留原始成功消息供日志记录
             original_success_message = result.get("message", "连接成功，但原始消息丢失")
             日志记录器.info(f"原始 test_connection 成功消息 for {std_provider_name}/{request.model}: {original_success_message}")
             # 为前端提供标准化的成功消息
             result["message"] = f"连接成功: 提供商 '{std_provider_name}', 模型 '{request.model}'"
        # --- 新增修改结束 ---

        日志记录器.info(f"模型测试结果 for {std_provider_name}/{request.model}: Status='{result.get('status')}', Message='{result.get('message')}'")
        return JSONResponse(content=result)

    except (ConfigurationError, APIError) as e:
        日志记录器.error(f"测试模型连接时捕获到配置或API错误 (Provider='{std_provider_name}', Model='{request.model}'): {e}", exc_info=True)
        # 这些是预期的业务逻辑错误，返回具体信息
        return JSONResponse(
            status_code=400, # Bad Request 可能更合适，因为是配置或API问题
            content={"status": "error", "message": f"测试失败 ({type(e).__name__}): {str(e)}"}
        )
    except HTTPException as e:
        # 重新抛出由 get_handler 或其他地方引发的 HTTPException
        raise e
    except Exception as e:
        日志记录器.error(f"测试模型连接时发生意外错误 (Provider='{std_provider_name}', Model='{request.model}'): {e}", exc_info=True)
        # 对于其他意外错误，返回通用错误信息
        raise HTTPException(status_code=500, detail=f"测试连接时发生意外错误: {str(e)}")

