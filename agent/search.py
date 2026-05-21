"""Multi-source search executors: web, arxiv, github, news."""
import asyncio
import httpx
from typing import List, Dict
from urllib.parse import quote_plus
from .config import SERPAPI_KEY, TAVILY_KEY, BRAVE_API_KEY


async def search_web(query: str, limit: int = 5) -> List[Dict]:
    """Web search — Tavily preferred, fallback Brave, fallback DuckDuckGo HTML."""
    if TAVILY_KEY:
        return await _search_tavily(query, limit)
    if BRAVE_API_KEY:
        return await _search_brave(query, limit)
    return await _search_ddg(query, limit)


async def _search_tavily(query: str, limit: int) -> List[Dict]:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            "https://api.tavily.com/search",
            json={"api_key": TAVILY_KEY, "query": query, "max_results": limit, "include_raw_content": False},
        )
        r.raise_for_status()
        data = r.json()
        return [{"url": x["url"], "title": x["title"], "snippet": x.get("content", "")[:500]} 
                for x in data.get("results", [])]


async def _search_brave(query: str, limit: int) -> List[Dict]:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": limit},
            headers={"X-Subscription-Token": BRAVE_API_KEY, "Accept": "application/json"},
        )
        r.raise_for_status()
        data = r.json()
        return [{"url": x["url"], "title": x["title"], "snippet": x.get("description", "")[:500]}
                for x in data.get("web", {}).get("results", [])[:limit]]


async def _search_ddg(query: str, limit: int) -> List[Dict]:
    """DuckDuckGo HTML scrape (no API key needed)."""
    from bs4 import BeautifulSoup
    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "Mozilla/5.0"}) as c:
        r = await c.get(f"https://html.duckduckgo.com/html/?q={quote_plus(query)}")
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for div in soup.select(".result")[:limit]:
            title_el = div.select_one(".result__title a")
            snippet_el = div.select_one(".result__snippet")
            if not title_el: continue
            results.append({
                "url": title_el.get("href", ""),
                "title": title_el.get_text(strip=True),
                "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
            })
        return results


async def search_arxiv(query: str, limit: int = 5) -> List[Dict]:
    """arXiv API."""
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(
            "http://export.arxiv.org/api/query",
            params={"search_query": f"all:{query}", "max_results": limit, "sortBy": "relevance"},
        )
        r.raise_for_status()
        # Parse Atom XML
        from xml.etree import ElementTree as ET
        root = ET.fromstring(r.text)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        results = []
        for entry in root.findall("a:entry", ns):
            title = (entry.find("a:title", ns).text or "").strip().replace("\n", " ")
            summary = (entry.find("a:summary", ns).text or "").strip().replace("\n", " ")[:500]
            link = entry.find("a:id", ns).text
            results.append({"url": link, "title": title, "snippet": summary})
        return results


async def search_github(query: str, limit: int = 5) -> List[Dict]:
    """GitHub repository search."""
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(
            "https://api.github.com/search/repositories",
            params={"q": query, "per_page": limit, "sort": "stars"},
        )
        r.raise_for_status()
        data = r.json()
        return [{
            "url": x["html_url"],
            "title": f"{x['full_name']} ⭐{x['stargazers_count']}",
            "snippet": (x.get("description") or "")[:500],
        } for x in data.get("items", [])]


async def search_news(query: str, limit: int = 5) -> List[Dict]:
    """News via Tavily news mode or web search with 'site:news'."""
    if TAVILY_KEY:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                "https://api.tavily.com/search",
                json={"api_key": TAVILY_KEY, "query": query, "topic": "news", "max_results": limit},
            )
            data = r.json()
            return [{"url": x["url"], "title": x["title"], "snippet": x.get("content", "")[:500]}
                    for x in data.get("results", [])]
    return await search_web(f"{query} news 2026", limit)


SEARCH_HANDLERS = {
    "web": search_web,
    "arxiv": search_arxiv,
    "github": search_github,
    "news": search_news,
}


async def execute_search(query: str, source: str = "web", limit: int = 5) -> List[Dict]:
    """Dispatch to correct search handler. Adds quality scoring."""
    handler = SEARCH_HANDLERS.get(source, search_web)
    try:
        results = await handler(query, limit)
    except Exception:
        # Fallback to web
        if source != "web":
            results = await search_web(query, limit)
        else:
            results = []
    # Add quality score + sort
    from .quality import rank_sources
    return rank_sources(results)
