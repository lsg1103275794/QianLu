"""
Text chunk splitter for dividing long texts into manageable chunks.
"""
from typing import List
from src.utils.logging import logger

class ChunkSplitter:
    def __init__(self, max_chunk_size: int = 2000, overlap: int = 200):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    def split_text(self, text: str) -> List[str]:
        """Split text into chunks of manageable size."""
        try:
            if len(text) <= self.max_chunk_size:
                return [text]

            chunks = []
            start = 0

            while start < len(text):
                # 计算当前块的结束位置
                end = start + self.max_chunk_size

                # 如果已经到达文本末尾
                if end >= len(text):
                    chunks.append(text[start:])
                    break

                # 尝试在句子边界处分割
                sentence_end = text.rfind('.', start, end)
                if sentence_end != -1:
                    end = sentence_end + 1

                # 添加当前块
                chunks.append(text[start:end])

                # 更新起始位置，考虑重叠
                start = end - self.overlap

            return chunks

        except Exception as e:
            logger.error(f"Error splitting text: {str(e)}")
            raise 