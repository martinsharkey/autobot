"""autobot.web_search - Web search tool for overnight learning.

Provides web search capability via HTTP requests with content filtering.
Used when Hermes' native web_search is unavailable.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Content filtering
BLOCKED_KEYWORDS = [
    "porn", "xxx", "adult", "nude", "nsfw", "escort", "sex", "naked",
    "gambling", "casino", "betting", "sportsbook", "poker", "slot machine",
    "explicit", "erotic", "hentai", "webcam model",
]

BLOCKED_DOMAINS = [
    "pornhub.com", "xvideos.com", "xnxx.com", "redtube.com",
    "youporn.com", "tube8.com", "spankbang.com", "xhamster.com",
    "betway.com", "bet365.com", "williamhill.com", "paddypower.com",
    "888casino.com",
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def is_url_allowed(url: str) -> bool:
    url_lower = url.lower()
    for domain in BLOCKED_DOMAINS:
        if domain in url_lower:
            return False
    return True


def is_research_topic_allowed(topic: str) -> bool:
    topic_lower = topic.lower()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in topic_lower:
            logger.warning(f"Blocked research topic: {keyword} in '{topic}'")
            return False
    return True


def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo HTML endpoint."""
    if not is_research_topic_allowed(query):
        return "BLOCKED: Research topic violates content policy."

    try:
        import httpx
        
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        data = {
            "q": query,
            "b": "",
            "kl": "",
        }
        
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.post(url, headers=headers, data=data)
            resp.raise_for_status()
            html = resp.text
        
        # Extract results from DuckDuckGo HTML
        results = []
        link_pattern = re.compile(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL)
        snippet_elems = re.findall(r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>', html, re.DOTALL)
        
        links = link_pattern.findall(html)
        
        for i, (href, title) in enumerate(links[:max_results]):
            if is_url_allowed(href):
                # Clean title
                title = re.sub(r'<[^>]+>', '', title).strip()
                snippet = re.sub(r'<[^>]+>', '', snippet_elems[i]).strip() if i < len(snippet_elems) else ""
                # Filter out ad redirects
                if 'duckduckgo.com/y.js' in href:
                    continue
                results.append({
                    "title": title,
                    "url": href,
                    "snippet": snippet[:200]
                })
        
        if not results:
            return json.dumps({"query": query, "results": [], "note": "No results found"}, indent=2)
        
        return json.dumps({"query": query, "results": results}, indent=2)
    
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return json.dumps({"query": query, "error": str(e)}, indent=2)


def web_fetch(url: str, max_chars: int = 5000) -> str:
    """Fetch a web page and extract text content."""
    if not is_url_allowed(url):
        return "BLOCKED: URL violates content policy."
    
    try:
        import httpx
        import re
        
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            html = resp.text
        
        # Strip HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text[:max_chars]
    
    except Exception as e:
        logger.error(f"Web fetch failed for {url}: {e}")
        return json.dumps({"url": url, "error": str(e)}, indent=2)


def get_tool_definition() -> Dict[str, Any]:
    """Return OpenAI tool definition for web_search."""
    return {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information. Returns up to 5 results with titles, URLs, and descriptions. Content filtered for professional use only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query. Must be professional/trading related.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    }


def get_fetch_tool_definition() -> Dict[str, Any]:
    """Return OpenAI tool definition for web_fetch."""
    return {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch a web page and extract text content. URL must be professional/trading related.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch",
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Maximum characters to return",
                        "default": 5000,
                    },
                },
                "required": ["url"],
            },
        },
    }


# Tool handler for Hermes integration
def handle_web_search(args: Dict[str, Any]) -> str:
    """Handle web_search tool call."""
    query = args.get("query", "")
    max_results = args.get("max_results", 5)
    return web_search(query, max_results)


def handle_web_fetch(args: Dict[str, Any]) -> str:
    """Handle web_fetch tool call."""
    url = args.get("url", "")
    max_chars = args.get("max_chars", 5000)
    return web_fetch(url, max_chars)

