"""
Retry utility for GlyphMind service.
"""
import time
from functools import wraps
from typing import Any, Callable, Optional, Type, Union
from .error_handler import APIError

def retry(
    exceptions: Union[Type[Exception], tuple[Type[Exception], ...]] = Exception,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    logger: Optional[Any] = None
) -> Callable:
    """
    Retry decorator for handling transient failures.
    
    Args:
        exceptions: Exception type(s) to catch
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        logger: Logger instance for logging retry attempts
    
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        raise APIError(
                            message=f"Operation failed after {max_attempts} attempts",
                            detail=str(e),
                            code=500
                        )
                    
                    if logger:
                        logger.warning(
                            f"Attempt {attempt + 1} failed: {str(e)}. "
                            f"Retrying in {current_delay} seconds..."
                        )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            raise APIError(
                message="Operation failed after maximum retry attempts",
                code=500
            )
        return wrapper
    return decorator

def is_retryable_exception(exception: Exception) -> bool:
    """Check if an exception is retryable.
    
    Args:
        exception: The exception to check
        
    Returns:
        bool: True if the exception is retryable, False otherwise
    """
    retryable_exceptions = (
        ConnectionError,
        TimeoutError,
        APIError
    )
    
    return isinstance(exception, retryable_exceptions)

# List of HTTP status codes that should trigger a retry
RETRY_STATUS_CODES = {
    408,  # Request Timeout
    429,  # Too Many Requests
    500,  # Internal Server Error
    502,  # Bad Gateway
    503,  # Service Unavailable
    504,  # Gateway Timeout
} 