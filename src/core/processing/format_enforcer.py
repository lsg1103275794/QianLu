"""
Format enforcer for ensuring consistent response formats.
"""
import re
from typing import Dict, Any
from src.utils.logging import logger

class FormatEnforcer:
    def __init__(self):
        self.analysis_pattern = re.compile(r"1\..*?(?=2\.|$)", re.DOTALL)
        self.score_pattern = re.compile(r"2\..*?(?=3\.|$)", re.DOTALL)
        self.suggestions_pattern = re.compile(r"3\..*?$", re.DOTALL)

    def enforce_format(self, text: str) -> Dict[str, Any]:
        """Enforce consistent format on the response text."""
        try:
            # 提取分析部分
            analysis_match = self.analysis_pattern.search(text)
            analysis = analysis_match.group(0).strip() if analysis_match else ""

            # 提取分数部分
            score_match = self.score_pattern.search(text)
            score_text = score_match.group(0).strip() if score_match else ""
            try:
                score = float(re.search(r"\d+", score_text).group())
            except (AttributeError, ValueError):
                score = 0.0

            # 提取建议部分
            suggestions_match = self.suggestions_pattern.search(text)
            suggestions_text = suggestions_match.group(0).strip() if suggestions_match else ""
            suggestions = [s.strip() for s in suggestions_text.split('\n') if s.strip()]

            return {
                "analysis": analysis,
                "score": score,
                "suggestions": suggestions
            }

        except Exception as e:
            logger.error(f"Error enforcing format: {str(e)}")
            raise 