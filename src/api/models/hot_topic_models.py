from pydantic import BaseModel, HttpUrl
from typing import Optional, List
import datetime

class HotTopicItem(BaseModel):
    id: str  # Unique identifier for the topic
    title: str
    summary: Optional[str] = None
    source_url: Optional[HttpUrl] = None
    source_name: str  # e.g., "新华网", "BBC News"
    source_type: str # e.g., "cn_authoritative", "cn_extranet"
    categories: Optional[List[str]] = None # e.g., ["科技", "财经"]
    published_at: Optional[datetime.datetime] = None
    retrieved_at: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)
    relevance_score: Optional[float] = None # Score assigned by LLM or other ranking logic
    raw_content: Optional[str] = None # Optional raw content fetched
    # For multi-source comparison
    related_articles: Optional[List[HttpUrl]] = None 
    analysis_summary: Optional[str] = None # LLM-generated summary if multiple sources are compared

class HotTopicRequest(BaseModel):
    categories: Optional[List[str]] = None
    count: int = 10 # Default number of topics to fetch

class HotTopicResponse(BaseModel):
    topics: List[HotTopicItem]
    last_updated: datetime.datetime
    message: Optional[str] = None 