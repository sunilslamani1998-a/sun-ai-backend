"""Source-backed web research using Tavily; retrieved page text is always untrusted."""
from __future__ import annotations
from typing import Any
from urllib.parse import urlparse
import httpx
from config import settings

class ResearchConfigurationError(RuntimeError):
    pass
class ResearchProviderError(RuntimeError):
    pass

def _valid_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and not parsed.username and not parsed.password
    except Exception:
        return False

async def search_web(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    query = query.strip()
    if not query:
        raise ValueError("Research query cannot be empty.")
    if len(query) > 500:
        raise ValueError("Research query is too long.")
    key = settings.tavily_api_key.get_secret_value().strip()
    if not key:
        raise ResearchConfigurationError("Web research is not configured. Set TAVILY_API_KEY.")
    limit = max(1, min(int(max_results), settings.research_max_results, 10))
    payload = {"api_key": key, "query": query, "search_depth": "advanced", "max_results": limit, "include_raw_content": False}
    try:
        async with httpx.AsyncClient(timeout=settings.research_timeout_seconds) as client:
            response = await client.post("https://api.tavily.com/search", json=payload)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ResearchProviderError("The web research provider request failed.") from exc
    raw = data.get("results", []) if isinstance(data, dict) else []
    results = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip()
        title = str(item.get("title", "")).strip()[:500]
        content = str(item.get("content", "")).strip()[:5000]
        if _valid_http_url(url) and (title or content):
            results.append({"title": title or url, "url": url, "content": content, "published_date": item.get("published_date")})
    return results
