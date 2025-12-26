"""
Main application entry point (simplified wrapper around backend_main.py).
This file exists to simplify menu integration and maintain compatibility.
"""
import sys
import os
from pathlib import Path

# 获取项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent

# 确保backend_main.py在Python路径中
sys.path.insert(0, str(PROJECT_ROOT))

# 从backend_main.py导入所需内容
from backend_main import create_app

# 当直接运行此文件时
if __name__ == "__main__":
    import uvicorn
    from src.utils.logging import logger
    
    logger.info("Starting application via main.py wrapper...")
    app_instance = create_app()
    
    # 与backend_main.py使用相同的启动配置
    uvicorn.run(
        app_instance,
        host="0.0.0.0",
        port=8000,
        access_log=True,
        log_level="debug"
    ) 