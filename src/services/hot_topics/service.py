from typing import List, Optional
from src.api.models.hot_topic_models import HotTopicItem, HotTopicRequest
from src.services.hot_topics.handler import (
    fetch_from_cn_authoritative_media, 
    fetch_from_cn_extranet_news,
    process_raw_topic # Assuming this is still relevant after web_search changes
)
import asyncio
import datetime

# Configuration for news sources (ideally this would come from a config file or DB)
# These keywords will be used by the web_search function in handler.py
CN_AUTHORITATIVE_SITE_KEYWORDS = ["news.cn", "people.com.cn", "cctv.com"] # Example site keywords
CN_EXTRANET_SOURCE_NAMES = ["BBC Chinese", "Reuters Chinese", "Wall Street Journal Chinese"] # Example source names for search

class HotTopicsService:
    async def get_hot_topics(self, request: HotTopicRequest) -> List[HotTopicItem]:
        """
        Main service method to get hot topics.
        Orchestrates fetching, processing, and ranking.
        """
        print(f"[HotTopicsService] Fetching hot topics with request: {request}")
        
        # Fetch raw data using web search via handler functions
        # These handler functions now use perform_web_search internally
        tasks = [
            fetch_from_cn_authoritative_media(CN_AUTHORITATIVE_SITE_KEYWORDS),
            fetch_from_cn_extranet_news(CN_EXTRANET_SOURCE_NAMES)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        raw_authoritative_data = results[0] if not isinstance(results[0], Exception) else []
        raw_extranet_data = results[1] if not isinstance(results[1], Exception) else []

        if isinstance(results[0], Exception):
            print(f"[HotTopicsService] Error fetching from authoritative media: {results[0]}")
        if isinstance(results[1], Exception):
            print(f"[HotTopicsService] Error fetching from extranet news: {results[1]}")

        all_hot_topics: List[HotTopicItem] = []

        print(f"[HotTopicsService] Processing {len(raw_authoritative_data)} items from authoritative media.")
        for raw_topic_data in raw_authoritative_data:
            # process_raw_topic expects a dict, and search results are already dicts
            # We need to ensure the keys match what process_raw_topic expects, or adapt it.
            # For now, assuming direct compatibility or that process_raw_topic is robust.
            all_hot_topics.append(process_raw_topic(raw_topic_data, source_type="cn_authoritative"))
        
        print(f"[HotTopicsService] Processing {len(raw_extranet_data)} items from extranet news.")
        for raw_topic_data in raw_extranet_data:
            all_hot_topics.append(process_raw_topic(raw_topic_data, source_type="cn_extranet"))

        # 1. LLM Processing Stage (Placeholder - to be implemented)
        print(f"[HotTopicsService] Current topic count before LLM: {len(all_hot_topics)}")
        all_hot_topics = await self.llm_process_topics(all_hot_topics, request)
        print(f"[HotTopicsService] Placeholder for LLM processing completed. Topics count: {len(all_hot_topics)}")

        # 2. Deduplication (Placeholder)
        # deduped_topics = self.deduplicate_topics(all_hot_topics)
        # all_hot_topics = deduped_topics
        # print(f"[HotTopicsService] Placeholder for deduplication. Topics count after: {len(all_hot_topics)}")

        # 3. Filtering by request.categories (Placeholder - LLM should fill categories)
        if request.categories and request.categories:
            # This filtering should happen AFTER LLM populates categories
            # all_hot_topics = [t for t in all_hot_topics if t.categories and any(cat in request.categories for cat in t.categories)]
            print(f"[HotTopicsService] Placeholder for category filtering: {request.categories}. Topics count: {len(all_hot_topics)}")

        # 4. Sorting (Placeholder - by relevance_score from LLM, then published_at)
        all_hot_topics.sort(key=lambda t: (t.relevance_score or 0, t.published_at or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)), reverse=True)
        print(f"[HotTopicsService] Placeholder for sorting. Topics count: {len(all_hot_topics)}")

        # 5. Limit by request.count
        final_topics = all_hot_topics[:request.count]
        print(f"[HotTopicsService] Limited to {len(final_topics)} topics by request.count.")
        return final_topics

    async def llm_process_topics(self, topics: List[HotTopicItem], request: HotTopicRequest) -> List[HotTopicItem]:
        """
        Placeholder for LLM processing. 
        This would involve calling your LLM (MCP) to:
        - Generate summaries from raw_content (if snippet from search is too short or needs refinement)
        - Extract/confirm categories.
        - Identify related articles across sources for the same event (for '多源参考对比').
        - Generate 'analysis_summary' if multiple sources cover the same event.
        - Assign 'relevance_score' based on timeliness, importance, content etc.
        """
        print(f"[HotTopicsService-LLM] LLM processing would happen here for {len(topics)} topics.")
        # Example: Iterate and enrich topics (this is highly simplified)
        for topic in topics:
            if not topic.summary and topic.raw_content: # If no summary from search, or want LLM to generate
                # topic.summary = await your_llm.summarize(topic.raw_content) # Placeholder
                topic.summary = f"LLM summary for: {topic.title[:30]}..." # Mock LLM summary
            
            # topic.categories = await your_llm.categorize(topic.title + " " + (topic.summary or topic.raw_content or ""))
            if not topic.categories: # Mock categories if LLM didn't provide
                 topic.categories = ["综合新闻"] if len(topic.title) % 2 == 0 else ["社会焦点", "科技前沿"]

            # topic.relevance_score = await your_llm.score_relevance(topic.title + " " + (topic.summary or ""))
            topic.relevance_score = round(len(topic.title) / (len(topic.title) + 50), 2) # Mock score

            # Multi-source analysis and analysis_summary would be more complex
        return topics

    def deduplicate_topics(self, topics: List[HotTopicItem]) -> List[HotTopicItem]:
        """Placeholder for deduplication logic."""
        # Simple deduplication by URL for now, more advanced logic needed
        print(f"[HotTopicsService] Deduplicating {len(topics)} topics by URL.")
        seen_urls = set()
        deduped = []
        for topic in topics:
            if topic.source_url and str(topic.source_url) in seen_urls:
                print(f"[HotTopicsService] Duplicate found and removed: {topic.source_url}")
                continue
            if topic.source_url:
                seen_urls.add(str(topic.source_url))
            deduped.append(topic)
        print(f"[HotTopicsService] Deduplication resulted in {len(deduped)} topics.")
        return deduped

# --- Test Code --- 
async def main_test():
    print("--- Starting HotTopicsService Test ---")
    service = HotTopicsService()
    
    # Test Case 1: Default request
    print("\n--- Test Case 1: Default Request ---")
    req1 = HotTopicRequest(count=3)
    print(f"Sending Request: HotTopicRequest(count={req1.count}, categories={req1.categories})")
    hot_topics1 = await service.get_hot_topics(req1)
    print(f"\n--- Received {len(hot_topics1)} Topics for Test Case 1 ---")
    for i, topic in enumerate(hot_topics1):
        print(f"\nTopic #{i+1}:")
        print(f"  ID: {topic.id}")
        print(f"  Title: {topic.title}")
        print(f"  Source: {topic.source_name} ({topic.source_type})")
        print(f"  URL: {topic.source_url}")
        print(f"  Published: {topic.published_at}")
        # print(f"  Retrieved: {topic.retrieved_at}") # Can be verbose
        print(f"  LLM Summary: {topic.summary}") 
        # print(f"  Raw Content (from search): {topic.raw_content[:60] if topic.raw_content else 'N/A'}...")
        print(f"  Categories: {topic.categories}")
        print(f"  Relevance Score: {topic.relevance_score}")
        # print(f"  Analysis Summary: {topic.analysis_summary}")

    # Test Case 2: Request with categories (currently placeholder filtering)
    # print("\n--- Test Case 2: Request with Categories (Placeholder Filtering) ---")
    # req2 = HotTopicRequest(count=2, categories=["科技"])
    # print(f"Sending Request: HotTopicRequest(count={req2.count}, categories={req2.categories})")
    # hot_topics2 = await service.get_hot_topics(req2)
    # print(f"\n--- Received {len(hot_topics2)} Topics for Test Case 2 ---")
    # for i, topic in enumerate(hot_topics2):
    #     print(f"  Topic #{i+1}: {topic.title} (Categories: {topic.categories}, Score: {topic.relevance_score})")

    print("\n--- HotTopicsService Test Completed ---")

if __name__ == "__main__":
    # Ensure you have an event loop for asyncio if running directly
    # For simple scripts, asyncio.run() is fine.
    # If integrating into a larger async framework like FastAPI, it handles the loop.
    asyncio.run(main_test()) 