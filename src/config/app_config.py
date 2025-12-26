# src/config/app_config.py
import yaml
from pydantic import BaseModel, Field, ValidationError
from pathlib import Path
import logging
from typing import Optional

# 尝试导入全局错误类型，如果失败则定义局部类型
try:
    from src.validation.error_handler import ConfigurationError
except ImportError:
    class ConfigurationError(Exception):
        """Custom exception for configuration errors."""
        pass

logger = logging.getLogger(__name__)

class AppConfig(BaseModel):
    """Application Configuration Model"""
    logging_level: str = Field("INFO", description="Logging level (e.g., DEBUG, INFO, WARNING, ERROR)")
    # Add other configuration fields here as your application needs them
    # Example:
    # upload_dir: str = Field("data/uploads", description="Directory for file uploads")
    # cache_dir: str = Field("data/cache", description="Directory for caching")

def load_config(config_path: Path) -> AppConfig:
    """Loads application configuration from a YAML file."""
    try:
        if not config_path.exists():
            logger.warning(f"Configuration file not found at {config_path}. Using default configuration.")
            # Create default config file if it doesn't exist
            default_config_data = {"logging_level": "INFO"}
            try:
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(default_config_data, f, default_flow_style=False)
                logger.info(f"Created default configuration file at {config_path}")
                return AppConfig(**default_config_data)
            except Exception as e:
                logger.error(f"Failed to create default config file at {config_path}: {e}")
                # Fallback to Pydantic defaults if file creation fails
                return AppConfig()

        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
            if not config_data: # Handle empty file case
                 logger.warning(f"Configuration file {config_path} is empty. Using default configuration.")
                 return AppConfig()
            return AppConfig(**config_data)
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration file {config_path}: {e}")
        raise ConfigurationError(f"Invalid YAML format in {config_path}") from e
    except ValidationError as e:
        logger.error(f"Configuration validation error in {config_path}: {e}")
        # Provide more specific error details
        error_details = e.errors()
        error_messages = [f"Field '{err['loc'][0]}': {err['msg']}" for err in error_details]
        detailed_error_msg = f"Invalid configuration data in {config_path}: {'; '.join(error_messages)}"
        raise ConfigurationError(detailed_error_msg) from e
    except Exception as e:
        logger.error(f"Failed to load configuration from {config_path}: {e}", exc_info=True)
        # Fallback to Pydantic defaults in case of unexpected errors
        logger.warning("Falling back to default configuration due to loading error.")
        return AppConfig() 