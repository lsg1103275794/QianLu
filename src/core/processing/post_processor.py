"""
Post-processor for cleaning and formatting analysis results.
"""
import re
from typing import Dict, Any
from src.utils.logging import logger

class PostProcessor:
    def __init__(self):
        self.cleanup_patterns = [
            (r"\n+", "\n"),  # 合并多个换行
            (r"\s+", " "),   # 合并多个空格
            (r"^\s+|\s+$", ""),  # 去除首尾空白
        ]

    def process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Process and clean up the analysis result."""
        try:
            # 清理分析文本
            analysis = result["analysis"]
            for pattern, replacement in self.cleanup_patterns:
                analysis = re.sub(pattern, replacement, analysis)
            result["analysis"] = analysis.strip()

            # 清理建议列表
            suggestions = result["suggestions"]
            cleaned_suggestions = []
            for suggestion in suggestions:
                for pattern, replacement in self.cleanup_patterns:
                    suggestion = re.sub(pattern, replacement, suggestion)
                cleaned_suggestions.append(suggestion.strip())
            result["suggestions"] = [s for s in cleaned_suggestions if s]

            # 确保分数在有效范围内
            score = result["score"]
            if not 0 <= score <= 100:
                score = max(0, min(100, score))
                result["score"] = score

            return result

        except Exception as e:
            logger.error(f"Error post-processing result: {str(e)}")
            raise 