"""
Style validator for ensuring consistent writing style in responses.
"""
import re
from typing import Dict, Any
from src.utils.logging import logger
from .format_enforcer import FormatEnforcer

class StyleValidator:
    def __init__(self):
        self.required_sections = ["analysis", "score", "suggestions"]
        self.style_rules = {
            "analysis": {
                "min_length": 100,
                "max_length": 2000,
                "required_keywords": ["分析", "特点", "风格"]
            },
            "score": {
                "min_value": 0,
                "max_value": 100,
                "format": r"^\d+(\.\d+)?$"
            },
            "suggestions": {
                "min_count": 1,
                "max_count": 10,
                "min_length": 10,
                "max_length": 200
            }
        }

    def validate_response(self, response: str) -> Dict[str, Any]:
        """Validate the response format and style."""
        try:
            # 使用格式强制器确保基本格式
            format_enforcer = FormatEnforcer()
            formatted_response = format_enforcer.enforce_format(response)

            # 验证分析部分
            analysis = formatted_response["analysis"]
            if len(analysis) < self.style_rules["analysis"]["min_length"]:
                raise ValueError("Analysis section is too short")
            if len(analysis) > self.style_rules["analysis"]["max_length"]:
                raise ValueError("Analysis section is too long")
            for keyword in self.style_rules["analysis"]["required_keywords"]:
                if keyword not in analysis:
                    raise ValueError(f"Analysis section missing required keyword: {keyword}")

            # 验证分数部分
            score = formatted_response["score"]
            if not self.style_rules["score"]["min_value"] <= score <= self.style_rules["score"]["max_value"]:
                raise ValueError("Score is out of valid range")
            if not re.match(self.style_rules["score"]["format"], str(score)):
                raise ValueError("Invalid score format")

            # 验证建议部分
            suggestions = formatted_response["suggestions"]
            if len(suggestions) < self.style_rules["suggestions"]["min_count"]:
                raise ValueError("Too few suggestions")
            if len(suggestions) > self.style_rules["suggestions"]["max_count"]:
                raise ValueError("Too many suggestions")
            for suggestion in suggestions:
                if len(suggestion) < self.style_rules["suggestions"]["min_length"]:
                    raise ValueError("Suggestion is too short")
                if len(suggestion) > self.style_rules["suggestions"]["max_length"]:
                    raise ValueError("Suggestion is too long")

            return formatted_response

        except Exception as e:
            logger.error(f"Error validating response: {str(e)}")
            raise 