"""
配置相关的API路由
"""
from fastapi import APIRouter, HTTPException, Depends, Body, Query
from typing import Dict, Any, Optional, List, Union
import os
import json
import shutil
from pathlib import Path
from pydantic import BaseModel, Field
import subprocess
from dotenv import dotenv_values

# --- 导入配置好的 logger --- 
from src.utils.logging import logger 
# -------------------------

from src.utils.config import ConfigManager, update_dotenv_vars
from src.providers.factory import get_provider_metadata, get_all_provider_metadata

# 配置日志
# logger = logging.getLogger(__name__) # <--- 移除这一行

# 创建路由
router = APIRouter(tags=["settings"])

# 配置模型
class GlobalConfig(BaseModel):
    """全局配置模型"""
    default_provider: Optional[str] = None
    theme: Optional[str] = None
    language: Optional[str] = None
    first_run: Optional[bool] = None
    debug: Optional[bool] = None

class ProviderConfig(BaseModel):
    """提供商配置模型"""
    enabled: Optional[bool] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    api_version: Optional[str] = None
    default_model: Optional[str] = None
    organization_id: Optional[str] = None
    model_deploy_id: Optional[str] = None
    stream: Optional[bool] = None

# 添加API提供商请求模型
class AddProviderRequest(BaseModel):
    """添加API提供商请求模型"""
    env: Dict[str, str] = Field(..., description="环境变量配置")
    config: Dict[str, Any] = Field(..., description="提供商配置")
    is_openai_compatible: bool = Field(True, description="是否使用OpenAI兼容接口")
    
    class Config:
        """额外的模型配置"""
        # 允许额外的字段
        extra = "allow"
        # 允许类型转换，例如将数字转换为字符串
        arbitrary_types_allowed = True

# 添加依赖函数
def get_config_manager():
    return ConfigManager()

# --- 恢复保存所有设置的路由 ---
@router.post("/settings/save-all", summary="保存所有设置到.env")
async def save_all_settings(settings_data: Dict[str, Any] = Body(...)):
    """
    接收前端发送的环境变量键值对，并更新到 .env 文件。
    """
    logger.info(f"收到保存 .env 设置的请求 (类型改为Any): {settings_data}")
    try:
        # 将所有非 None 的值转换为字符串，以匹配 update_dotenv_vars 的期望
        settings_to_save = {k: str(v) for k, v in settings_data.items() if v is not None}
        # 对于值为 None 的键，我们也需要显式传递空字符串给 dotenv
        for k, v in settings_data.items():
            if v is None:
                settings_to_save[k] = ''
        
        logger.debug(f"转换后准备写入 .env 的数据: {settings_to_save}")
        success = update_dotenv_vars(settings_to_save)
        if success:
            logger.info("成功更新 .env 文件。")
            # 考虑是否需要重新加载配置或通知其他部分？
            # 目前只返回成功
            return {"message": "Settings saved successfully."}
        else:
            logger.error("调用 update_dotenv_vars 更新 .env 文件失败。")
            raise HTTPException(status_code=500, detail="Failed to save settings to .env file.")
    except Exception as e:
        logger.error(f"处理 /settings/save-all 请求时发生意外错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while saving settings.")

# --- 添加API提供商端点 ---
@router.post("/settings/add-provider", summary="添加新的API提供商")
async def add_provider(request: AddProviderRequest = Body(...)):
    # --- 添加最顶层的日志语句 --- 
    logger.critical("!!!!!!!!!!!!!!!!!!!!!! Entered add_provider function !!!!!!!!!!!!!!!!!!!!!!") 
    # --------------------------
    """
    添加新的API提供商。接收环境变量配置和提供商配置，
    生成OpenAI兼容的处理程序（如果适用），并保存配置到.env文件。
    """
    logger.info(f"收到添加API提供商请求: {request.config.get('name')}")
    
    reload_status = "not triggered"
    try:
        # 1. 从请求获取关键信息
        provider_name = request.config.get("name")
        display_name = request.config.get("display_name", provider_name)
        
        if not provider_name:
            raise HTTPException(status_code=400, detail="提供商名称不能为空")
        
        # 2. 检查提供商名称是否已存在
        all_providers = get_all_provider_metadata()
        existing_names = [p.get("standard_name") for p in all_providers]
        
        if provider_name in existing_names:
            logger.warning(f"尝试添加已存在的提供商: {provider_name}")
            # 我们允许更新现有提供商，但要记录警告
        
        # 3. 保存环境变量配置到.env（幂等，仅更新本 provider 相关 key）
        env_vars = request.env
        env_vars_str = {k: ("" if v is None else str(v)) for k, v in env_vars.items()}
        # 只更新本 provider 相关 key
        
        # 确保所有环境变量值为字符串
        env_vars_str = {}
        for k, v in env_vars.items():
            if v is None:
                env_vars_str[k] = ""
            else:
                env_vars_str[k] = str(v)
        
        # 屏蔽敏感信息用于日志记录
        safe_log_vars = {k: (v[:4] + "..." if k.endswith('API_KEY') and len(v) > 8 else v) 
                           for k, v in env_vars_str.items()}
        logger.debug(f"准备保存环境变量: {safe_log_vars}")
        
        # 调用update_dotenv_vars保存到.env
        provider_prefix = f"{provider_name.upper()}_"
        current_env = dotenv_values(".env")
        merged_env = dict(current_env)
        for k, v in env_vars_str.items():
            if k.startswith(provider_prefix):
                merged_env[k] = v
        # update_dotenv_vars 只写入 provider 相关 key
        update_success = update_dotenv_vars({k: v for k, v in merged_env.items() if k.startswith(provider_prefix)})
        if not update_success:
            logger.error(f"更新.env文件失败: {provider_name}")
            raise HTTPException(status_code=500, detail="更新环境变量配置失败")
        
        # 4. 如果是OpenAI兼容API，尝试创建处理程序文件
        auto_generated = False
        template_type = request.config.get('template_type', 'openai_compatible')
        template_params = request.config.get('template_params', {})
        handler_path = await create_handler_file(provider_name, display_name, template_type, template_params, request.config.get('schema', {}))
        if handler_path:
            auto_generated = True
            logger.info(f"成功为提供商 {provider_name} 创建处理程序文件: {handler_path}")
        
        # 5. 添加到providers_meta.json
        try:
            logger.critical("!!!!!!!!!!!!!!!!! BEFORE calling update_provider_metadata !!!!!!!!!!!!!!!!!") # 添加日志
            await update_provider_metadata(provider_name, display_name, request.is_openai_compatible)
            logger.critical("!!!!!!!!!!!!!!!!! AFTER calling update_provider_metadata !!!!!!!!!!!!!!!!!") # 添加日志
            logger.info(f"Successfully updated or added metadata for {provider_name}")
        except Exception as e:
            logger.error(f"更新提供商元数据失败: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"更新提供商元数据文件失败: {str(e)}")
        
        # 6. 自动生成 config/providers/{provider}.json
        try:
            config_dir = Path("config/providers")
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / f"{provider_name}.json"
            if config_path.exists():
                backup_path = config_path.with_suffix('.json.bak')
                shutil.copy2(config_path, backup_path)
                logger.info(f"已备份现有 provider config: {backup_path}")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(request.config, f, indent=2, ensure_ascii=False)
            logger.info(f"成功生成 provider config: {config_path}")
        except Exception as e:
            logger.error(f"生成 provider config 失败: {e}", exc_info=True)
        
        # 优先尝试 supervisor/pm2/docker/uvicorn
        cmds = [
            ["supervisorctl", "restart", "all"],
            ["pm2", "restart", "all"],
            ["docker", "restart", "aigc"],
            ["pkill", "-HUP", "uvicorn"]
        ]
        for cmd in cmds:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    reload_status = f"reloaded by: {' '.join(cmd)}"
                    logger.info(f"后端服务已重载: {' '.join(cmd)}")
                    break
            except Exception as e:
                logger.warning(f"尝试重载命令失败: {' '.join(cmd)}: {e}")
    except HTTPException as e:
        # 重新抛出已经捕获的HTTP异常
        raise e
    except Exception as e:
        logger.error(f"添加API提供商时发生错误: {e}", exc_info=True)
        reload_status = f"reload failed: {e}"
        raise HTTPException(status_code=500, detail=f"添加API提供商时发生内部错误: {str(e)}")

    return {
        "status": "success",
        "message": f"成功添加API提供商 {display_name}",
        "provider": provider_name,
        "auto_generated": auto_generated,
        "reload_status": reload_status
    }

async def create_handler_file(provider_name: str, display_name: str, template_type: str = 'openai_compatible', template_params: dict = None, schema: dict = None) -> Optional[str]:
    """
    基于模板类型和参数创建新的处理程序文件，并自动注入 schema 字段注释。
    """
    try:
        template_path = Path(f"src/providers/handlers/{template_type}_template.py")
        if not template_path.exists():
            logger.error(f"模板文件不存在: {template_path}")
            return None
        output_dir = Path("src/providers/handlers")
        output_path = output_dir / f"{provider_name}.py"
        if output_path.exists():
            backup_path = output_path.with_suffix('.py.bak')
            shutil.copy2(output_path, backup_path)
            logger.info(f"已备份现有处理程序文件: {backup_path}")
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        # 替换通用占位符
        class_name = f"{provider_name.title().replace('_', '')}Handler"
        template_content = template_content.replace("TemplateOpenAIHandler", class_name)
        template_content = template_content.replace(
            "Template for creating OpenAI-compatible API handlers.",
            f"{display_name} API handler (auto-generated)."
        )
        template_content = template_content.replace(
            "self.provider_name = config.get('provider_name', 'template_openai')",
            f"self.provider_name = config.get('provider_name', '{provider_name}')"
        )
        template_content = template_content.replace(
            "Note: This is a template file and should not be used directly.",
            f"Note: This is an auto-generated handler for {display_name}."
        )
        # 替换自定义参数 {{param}}
        if template_params:
            for k, v in template_params.items():
                template_content = template_content.replace(f"{{{{{k}}}}}", str(v))
        # 注入 schema 字段注释
        schema_comment = ""
        if schema and 'fields' in schema:
            import json
            schema_comment = f"""\n# === Provider Schema Fields (auto-generated) ===\n# {json.dumps(schema['fields'], indent=2, ensure_ascii=False)}\n# =============================================\n"""
        template_content = schema_comment + template_content
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
        logger.info(f"成功创建处理程序文件: {output_path}")
        return str(output_path)
    except Exception as e:
        logger.error(f"创建处理程序文件失败: {e}", exc_info=True)
        return None

async def update_provider_metadata(provider_name: str, display_name: str, is_openai_compatible: bool):
    """
    更新或添加提供商元数据到providers_meta.json文件，采用原子写入（临时文件+重命名）。
    """
    logger.critical("!!!!!!!!!!!!!!!!!!!!!! Entered update_provider_metadata function !!!!!!!!!!!!!!!!!!!!!!")
    from src.providers.factory import METADATA_FILE
    meta_path = Path(METADATA_FILE)
    logger.info(f"Attempting to update metadata file at: {meta_path}")
    try:
        meta_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as dir_err:
        logger.error(f"无法创建元数据目录 {meta_path.parent}: {dir_err}")
        raise IOError(f"无法创建元数据目录: {dir_err}") from dir_err
    metadata = []
    try:
        if meta_path.exists():
            with open(meta_path, 'r', encoding='utf-8') as f:
                try:
                    metadata = json.load(f)
                    if not isinstance(metadata, list):
                        logger.warning(f"元数据文件 {meta_path} 格式无效 (不是列表)，将使用空列表覆盖。")
                        metadata = []
                except json.JSONDecodeError:
                    logger.warning(f"元数据文件 {meta_path} JSON 解析失败，将使用空列表覆盖。")
                    metadata = []
        else:
            logger.info(f"元数据文件 {meta_path} 不存在，将创建新文件。")
            metadata = []
        provider_exists = False
        found_index = -1
        for i, provider in enumerate(metadata):
            if isinstance(provider, dict) and provider.get("standard_name") == provider_name:
                provider_exists = True
                found_index = i
                break
        new_provider_entry = {
            "standard_name": provider_name,
            "display_name": display_name,
            "env_prefix": f"{provider_name.upper()}_",
            "handler_module_path": f"src.providers.handlers.{provider_name}" if is_openai_compatible else f"src.providers.handlers.custom.{provider_name}",
            "handler_class_name": f"{provider_name.title().replace('_', '')}Handler",
            "aliases": [provider_name],
            "config_path": f"config/providers/{provider_name}.json"
        }
        if provider_exists and found_index != -1:
            metadata[found_index].update(new_provider_entry)
            logger.info(f"更新提供商元数据: {provider_name}")
        else:
            metadata.append(new_provider_entry)
            logger.info(f"添加新提供商元数据: {provider_name}")
        logger.debug(f"准备写入元数据 (共 {len(metadata)} 条): {metadata}")
        # 原子写入
        temp_meta_path = meta_path.with_suffix('.json.tmp')
        with open(temp_meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        os.replace(str(temp_meta_path), str(meta_path))
        logger.info(f"成功原子写入元数据文件: {meta_path}")
    except Exception as e:
        logger.error(f"更新或写入元数据文件 {meta_path} 时发生错误: {e}", exc_info=True)
        if 'temp_meta_path' in locals() and temp_meta_path.exists():
            try: temp_meta_path.unlink()
            except OSError: pass
        raise # Re-raise other critical errors

@router.get("/settings/provider-schema/{type}", summary="获取指定类型API的表单schema")
async def get_provider_schema(type: str):
    """
    根据type返回schema，优先查找 config/provider_config_template.json 或内置schema。
    """
    import json, os
    schema_path = os.path.join(os.path.dirname(__file__), '../../config/provider_config_template.json')
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            template = json.load(f)
        # 可根据type返回不同schema，现只返回通用模板
        return template
    except Exception as e:
        # 兜底返回通用OpenAI schema
        return {"fields": [
            {"name": "api_key", "label": "API密钥", "type": "password", "required": True},
            {"name": "endpoint", "label": "API服务地址", "type": "text", "required": True},
            {"name": "default_model", "label": "默认模型", "type": "text", "required": False},
            {"name": "temperature", "label": "Temperature", "type": "number", "default": 0.7},
            {"name": "max_tokens", "label": "Max Tokens", "type": "number", "default": 2048},
            {"name": "top_p", "label": "Top P", "type": "number", "default": 1.0}
        ]}

@router.get("/settings/providers-meta", summary="获取所有API提供商元数据")
async def get_providers_meta():
    """
    返回所有 provider 的元数据（含 env_prefix、handler_class_name、config_path 等）。
    """
    from src.providers.factory import get_all_provider_metadata
    return get_all_provider_metadata()

# You might have other setting-related routes below
# Example:
# @router.get("/settings/some-other-setting")
# async def get_some_setting(...):
#     pass 