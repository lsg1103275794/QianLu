"""
Logging utility for GlyphMind service.
"""
import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

class Logger:
    """Logger class for GlyphMind service"""
    
    def __init__(self):
        self.log_dir = Path('logs')
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """Setup logger with file and console handlers"""
        # Create logs directory if it doesn't exist
        self.log_dir.mkdir(exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger('glyphmind')
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )
        
        # Create file handler
        file_handler = RotatingFileHandler(
            self.log_dir / 'glyphmind.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'  # Explicitly set encoding
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        # console_handler.setFormatter(console_formatter) # Temporarily disable console handler
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        # self.logger.addHandler(console_handler) # Temporarily disable console handler
    
    def debug(self, message: str) -> None:
        """Log debug message"""
        self.logger.debug(message)
    
    def info(self, message: str) -> None:
        """Log info message"""
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """Log warning message"""
        self.logger.warning(message)
    
    def error(self, message: str, **kwargs) -> None:
        """
        Log error message
        
        Args:
            message: Error message to log
            **kwargs: Additional arguments to pass to logger.error
        """
        self.logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """
        Log critical message
        
        Args:
            message: Critical message to log
            **kwargs: Additional arguments to pass to logger.critical
        """
        self.logger.critical(message, **kwargs)

    def exception(self, message: str, **kwargs) -> None:
        """
        Log exception message with stack trace
        
        Args:
            message: Exception message to log
            **kwargs: Additional arguments to pass to logger.exception
                     Typically includes exc_info=True implicitly.
        """
        self.logger.exception(message, **kwargs)

# --- Create and export a configured logger instance --- 
logger = Logger().logger
# ---------------------------------------------------- 