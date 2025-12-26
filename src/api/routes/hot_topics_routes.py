from fastapi import APIRouter, Depends, HTTPException
from typing import List
from src.api.models.hot_topic_models import HotTopicItem, HotTopicRequest, HotTopicResponse
from src.services.hot_topics.service import HotTopicsService
import datetime

router = APIRouter()

# Dependency for HotTopicsService
# In a real app, you might have a more sophisticated dependency injection system
def get_hot_topics_service():
    return HotTopicsService()

@router.post("/hot-topics/", response_model=HotTopicResponse, tags=["Hot Topics"])
async def get_hot_topics_endpoint(
    request: HotTopicRequest,
    service: HotTopicsService = Depends(get_hot_topics_service)
):
    """
    Endpoint to fetch and process real-time hot topics.
    Accepts parameters like categories and count.
    """
    try:
        topics = await service.get_hot_topics(request)
        return HotTopicResponse(
            topics=topics,
            last_updated=datetime.datetime.now(datetime.timezone.utc),
            message=f"Successfully fetched {len(topics)} hot topics."
        )
    except Exception as e:
        # Log the exception e
        print(f"Error in /hot-topics/ endpoint: {e}") # Basic logging
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching hot topics: {str(e)}")

# You would then include this router in your main FastAPI application
# In your main.py or equivalent:
# from src.api.routes import hot_topics_routes
# app.include_router(hot_topics_routes.router, prefix="/api/v1") 