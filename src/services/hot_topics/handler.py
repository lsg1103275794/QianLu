from typing import List, Dict, Any, Optional
# import requests # Placeholder for actual HTTP requests
# from bs4 import BeautifulSoup # Placeholder for HTML parsing
from src.api.models.hot_topic_models import HotTopicItem # Assuming model is defined
import datetime
import uuid
import asyncio # Added for sleep in mock
import os # For environment variables
import json # For Serper API request
import requests # For making HTTP requests
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# Actual implementation of a web_search utility using Serper API
async def perform_web_search(query: str, site_filter: Optional[str] = None, lang: str = "en", num_results: int = 5) -> List[Dict[str, Any]]:
    """
    Performs a web search using Serper API.
    Args:
        query: The search query string.
        site_filter: Optional. Restricts search to a specific site (e.g., "example.com").
        lang: Optional. Language for search results (e.g., "en", "zh-cn"). Serper uses 'gl' (geolocation) and 'hl' (host language).
              We'll map common lang codes to Serper's 'gl' and 'hl'.
        num_results: Number of search results to fetch. Max typically 10-20 for Serper free/basic.
    Returns:
        A list of dictionaries, where each dictionary represents a search result.
    """
    if not SERPER_API_KEY:
        print("SERPER_API_KEY not found in environment variables. Please set it in .env")
        # Fallback to mock data or raise an error if API key is missing
        return await perform_mock_search(query, site_filter, lang) # Fallback to mock if key is missing

    url = "https://google.serper.dev/search"
    
    # Construct the payload for Serper
    # Mapping lang to Serper's gl (country) and hl (language)
    # This is a simplified mapping, Serper's actual geo/lang codes might be more specific
    gl_code = "us"
    hl_code = "en"
    if lang.lower() == "zh-cn":
        gl_code = "cn"
        hl_code = "zh-cn"
    # Add more language mappings if needed

    payload_dict = {
        "q": query if not site_filter else f"site:{site_filter} {query}",
        "gl": gl_code,
        "hl": hl_code,
        "num": num_results 
    }
    # Encode the payload to UTF-8 bytes before sending
    payload_utf8 = json.dumps(payload_dict).encode('utf-8')
    
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json; charset=utf-8' # Explicitly state charset in header
    }

    print(f"Performing Serper web search for: '{payload_dict['q']}' with gl:'{gl_code}', hl:'{hl_code}'")

    formatted_results = []
    try:
        # Using asyncio.to_thread for running synchronous requests in an async function
        # Pass the UTF-8 encoded bytes to the data parameter
        response = await asyncio.to_thread(requests.request, "POST", url, headers=headers, data=payload_utf8, timeout=10)
        
        # Ensure the response is treated as UTF-8, as this is expected for JSON APIs.
        # This helps if the server doesn't specify charset or specifies it incorrectly.
        if response.encoding is None or response.encoding.lower() not in ['utf-8', 'utf8']:
            response.encoding = 'utf-8'
            
        response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)
        search_data = response.json()

        # Process Serper results (structure might vary, check their documentation)
        # Common fields: 'organic' (list of results), 'title', 'link', 'snippet', 'position'
        if "organic" in search_data:
            for item in search_data["organic"][:num_results]: # Ensure we respect num_results
                # Try to get published date if available (Serper might not always provide it directly)
                # Placeholder for date extraction logic
                published_date_str = item.get("date") # Serper might have a 'date' field
                
                # If 'attributes' and 'PublishDate' exist (common in some rich snippets)
                if not published_date_str and item.get("attributes") and item["attributes"].get("PublishDate"):
                    published_date_str = item["attributes"]["PublishDate"]

                formatted_results.append({
                    "title": item.get("title", "N/A"),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source_name": item.get("source") or item.get("sitelinks_search_box") or item.get("domain", "Unknown Source"), # Attempt to get source
                    "raw_text_content": item.get("snippet", ""), # Initially, snippet is the raw content
                    "published_str": published_date_str, # This might be None or a string
                    # "position": item.get("position") # if you need the rank
                })
        else:
            print(f"Serper API Warning: 'organic' results not found in response. Query: {query}")
            print(f"Serper Response: {search_data}")


    except requests.exceptions.Timeout:
        print(f"Serper API request timed out for query: {query}")
        return await perform_mock_search(query, site_filter, lang) # Fallback
    except requests.exceptions.HTTPError as e:
        print(f"Serper API HTTP error for query: {query}: {e}")
        if e.response is not None:
            # Ensure the error response text is also decoded as UTF-8 before printing
            if e.response.encoding is None or e.response.encoding.lower() not in ['utf-8', 'utf8']:
                e.response.encoding = 'utf-8'
            print(f"Serper Response Status: {e.response.status_code}, Body: {e.response.text}")
        return await perform_mock_search(query, site_filter, lang) # Fallback
    except Exception as e:
        print(f"An error occurred during Serper web search for query {query}: {e}")
        return await perform_mock_search(query, site_filter, lang) # Fallback to mock on any error

    return formatted_results

# Keep the mock search function for fallback or if API key is not set
async def perform_mock_search(query: str, site_filter: Optional[str] = None, lang: str = "zh-CN") -> List[Dict[str, Any]]:
    """ 
    Mock web search function (renamed from previous perform_web_search).
    """
    print(f"Performing MOCK web search for: '{query}' with site_filter: '{site_filter}', lang: '{lang}'")
    await asyncio.sleep(0.1) # Simulate network delay
    results = []
    if "news.cn" in query or (site_filter and "news.cn" in site_filter):
        results.extend([
            {
                "title": "新华网权威报道1 - 来自模拟搜索",
                "url": "http://news.cn/mock1",
                "snippet": "这是新华网关于事件A的模拟搜索结果摘要...",
                "source_name": "新华网 (模拟)",
                "published_str": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "raw_text_content": "这是新华网关于事件A的模拟搜索结果摘要... [更多内容来自模拟搜索...]"
            },
            {
                "title": "新华网权威报道2 - 来自模拟搜索",
                "url": "http://news.cn/mock2",
                "snippet": "新华网对事件B的深度分析模拟摘要...",
                "source_name": "新华网 (模拟)",
                "published_str": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).isoformat(),
                "raw_text_content": "新华网对事件B的深度分析模拟摘要... [更多内容来自模拟搜索...]"
            }
        ])
    elif "people.com.cn" in query or (site_filter and "people.com.cn" in site_filter):
        results.extend([
            {
                "title": "人民网独家新闻 - 模拟搜索",
                "url": "http://people.com.cn/mock1",
                "snippet": "人民网追踪报道了重要动态C的模拟摘要...",
                "source_name": "人民网 (模拟)",
                "published_str": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=30)).isoformat(),
                "raw_text_content": "人民网追踪报道了重要动态C的模拟摘要... [更多内容来自模拟搜索...]"
            }
        ])
    elif "BBC Chinese" in query:
        results.extend([
            {
                "title": "BBC中文网报道X (模拟搜索)",
                "url": "http://bbc.com/chinese/mock_x",
                "snippet": "BBC中文网观察到国际事件X的最新进展模拟摘要...",
                "source_name": "BBC Chinese (模拟)",
                "published_str": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)).isoformat(),
                "raw_text_content": "BBC中文网观察到国际事件X的最新进展模拟摘要... [更多内容来自模拟搜索...]"
            }
        ])
    elif "Reuters Chinese" in query:
        results.extend([
            {
                "title": "路透中文网分析Y (模拟搜索)",
                "url": "http://reuters.com/chinese/mock_y",
                "snippet": "路透中文网对市场趋势Y提供了分析模拟摘要...",
                "source_name": "Reuters Chinese (模拟)",
                "published_str": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1, minutes=15)).isoformat(),
                "raw_text_content": "路透中文网对市场趋势Y提供了分析模拟摘要... [更多内容来自模拟搜索...]"
            }
        ])
    else:
        results.append({
            "title": f"模拟搜索结果 for '{query}'",
            "url": f"http://example.com/search?q={query.replace(' ', '+')}",
            "snippet": f"这是一个关于'{query}'的通用模拟搜索摘要...",
            "source_name": "模拟搜索引擎",
            "published_str": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "raw_text_content": f"这是一个关于'{query}'的通用模拟搜索摘要... [更多内容来自模拟搜索...]"
        })
    return results

async def fetch_from_cn_authoritative_media(site_keywords: List[str]) -> List[Dict[str, Any]]:
    """
    Fetches raw news data from authoritative Chinese media using web search.
    site_keywords: List of keywords, could be domain names or official names.
    e.g., ["news.cn", "people.com.cn"]
    """
    all_raw_topics = []
    print(f"Fetching from CN authoritative media using web_search for: {site_keywords}")
    for keyword in site_keywords:
        # Formulate a query, e.g., search for recent news on the site
        # Query might be more sophisticated, like "最新 OR 今日 OR 头条 site:domain.com"
        query = f"最新 site:{keyword}" # Simple query for example
        # Alternatively, if the keyword IS the domain, use site_filter
        # query = "最新消息"
        # site_filter_param = keyword 
        try:
            # Assuming perform_web_search can take a site filter
            # For now, we'll just use a general query that includes the keyword
            search_results = await perform_web_search(query=f"{keyword} 最新新闻", lang="zh-CN")
            for res in search_results:
                res["source_name"] = res.get("source_name", keyword) # Ensure source name is set
            all_raw_topics.extend(search_results)
        except Exception as e:
            print(f"Error searching for {keyword}: {e}")
    return all_raw_topics

async def fetch_from_cn_extranet_news(source_names: List[str]) -> List[Dict[str, Any]]:
    """
    Fetches raw news data from Chinese extranet news sources using web search.
    source_names: List of names for the news sources, e.g., ["BBC Chinese", "Reuters Chinese"]
    """
    all_raw_topics = []
    print(f"Fetching from CN extranet news using web_search for: {source_names}")
    for name in source_names:
        query = f"{name} 最新报道"
        try:
            search_results = await perform_web_search(query=query, lang="zh-CN") # lang might need adjustment
            for res in search_results:
                res["source_name"] = res.get("source_name", name) # Ensure source name
            all_raw_topics.extend(search_results)
        except Exception as e:
            print(f"Error searching for {name}: {e}")
    return all_raw_topics

def process_raw_topic(raw_data: Dict[str, Any], source_type: str) -> HotTopicItem:
    """Converts a raw fetched data dictionary into a HotTopicItem object."""
    # Basic parsing for published_at - real implementation will be more robust
    published_time = None
    if raw_data.get("published_str"):
        try:
            published_time = datetime.datetime.fromisoformat(raw_data["published_str"].replace('Z', '+00:00'))
        except ValueError:
            published_time = None # Or log a warning

    return HotTopicItem(
        id=str(uuid.uuid4()),
        title=raw_data.get("title", "N/A"),
        summary=raw_data.get("summary"), # LLM will likely generate this later
        source_url=raw_data.get("url"),
        source_name=raw_data.get("source_name", "Unknown Source"),
        source_type=source_type,
        raw_content=raw_data.get("raw_text_content"),
        published_at=published_time,
        retrieved_at=datetime.datetime.now(datetime.timezone.utc)
    ) 