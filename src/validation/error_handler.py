# src/validation/error_handler.py

class BaseText2AlpacaError(Exception):
    """Base class for custom exceptions in this application."""
    pass

class ConfigurationError(BaseText2AlpacaError):
    """Exception raised for errors in configuration loading or validation."""
    def __init__(self, message="Configuration error", details=None):
        self.message = message
        self.details = details
        super().__init__(f"{message}{f': {details}' if details else ''}")

# 为了向后兼容，添加别名
ConfigError = ConfigurationError

class APIConnectionError(BaseText2AlpacaError):
    """Exception raised when unable to connect to the API endpoint."""
    def __init__(self, provider_name="Unknown Provider", details=None):
        self.provider_name = provider_name
        self.details = details
        super().__init__(f"API Connection Error ({provider_name}){f': {details}' if details else ''}")

class APIResponseError(BaseText2AlpacaError):
    """Exception raised for non-successful API responses (non-2xx status or invalid format)."""
    def __init__(self, provider_name="Unknown Provider", status_code=None, response_body=None, details=None):
        self.provider_name = provider_name
        self.status_code = status_code
        self.response_body = response_body
        self.details = details
        msg = f"API Response Error ({provider_name})"
        if status_code:
            msg += f" Status Code: {status_code}"
        if details:
            msg += f" Details: {details}"
        if response_body:
            preview = str(response_body)[:200] # Show preview
            msg += f" Response Body Preview: {preview}..."
        super().__init__(msg)

class APICallError(BaseText2AlpacaError):
    """Exception raised when errors occur during API call execution."""
    def __init__(self, message="API call failed", provider_name="Unknown Provider", details=None):
        self.message = message
        self.provider_name = provider_name
        self.details = details
        super().__init__(f"{message} ({provider_name}){f': {details}' if details else ''}")

class ValidationError(BaseText2AlpacaError):
    """Exception raised during data validation (e.g., style, format)."""
    def __init__(self, message="Validation error", validation_details=None):
        self.message = message
        self.validation_details = validation_details # Could be a list of errors
        super().__init__(f"{message}{f': {validation_details}' if validation_details else ''}")

# 添加缺失的异常类
class APIResponseFormatError(BaseText2AlpacaError):
    """Exception raised when the API response is not in the expected format."""
    def __init__(self, provider_name="Unknown Provider", details=None):
        self.provider_name = provider_name
        self.details = details
        super().__init__(f"API Response Format Error ({provider_name}){f': {details}' if details else ''}")

class APITimeoutError(BaseText2AlpacaError):
    """Exception raised when an API request times out."""
    def __init__(self, message=None, timeout_value=None, timeout_seconds=None, provider=None, provider_name=None, details=None):
        # 兼容所有 handler 的参数
        self.provider_name = provider or provider_name or "Unknown Provider"
        self.timeout_seconds = timeout_value or timeout_seconds
        self.details = details
        msg = message or f"API Timeout Error ({self.provider_name})"
        if self.timeout_seconds:
            msg += f" after {self.timeout_seconds}s"
        if details:
            msg += f": {details}"
        super().__init__(msg)

class APIError(BaseText2AlpacaError):
    """General API error, used as a catch-all for other API-related errors."""
    def __init__(self, message="API error occurred", provider_name="Unknown Provider", details=None):
        self.provider_name = provider_name
        self.message = message
        self.details = details
        super().__init__(f"{message} ({provider_name}){f': {details}' if details else ''}")

