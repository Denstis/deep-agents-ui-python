"""Internet tools for web search and URL fetching."""

from typing import Any, Literal
import os


def web_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
) -> dict[str, Any]:
    """Search the web using Tavily API for current information.
    
    This tool searches the web and returns relevant results with titles, URLs, and content.
    
    Args:
        query: The search query (be specific and detailed)
        max_results: Number of results to return (default: 5)
        topic: Search topic type - "general" for most queries, "news" for current events, "finance" for financial news
        
    Returns:
        Dictionary containing:
        - results: List of search results with title, url, content, score
        - query: The original search query
        - error: If an error occurred
        
    Example:
        >>> result = web_search("Python programming tutorials", max_results=3)
        >>> print(result["results"][0]["title"])
    """
    api_key = os.getenv("TAVILY_API_KEY")
    
    if not api_key:
        return {
            "error": "Tavily API key not configured. Set TAVILY_API_KEY environment variable.",
            "query": query,
            "results": [],
        }
    
    try:
        from tavily import TavilyClient
    except ImportError:
        return {
            "error": "tavily package not installed. Install with: pip install tavily",
            "query": query,
            "results": [],
        }
    
    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query,
            max_results=max_results,
            include_answer=True,
            topic=topic,
        )
        
        results = []
        for result in response.get("results", []):
            results.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
                "score": result.get("score", 0),
            })
        
        return {
            "query": query,
            "answer": response.get("answer", ""),
            "results": results,
        }
        
    except Exception as e:
        return {
            "error": f"Web search error: {str(e)}",
            "query": query,
            "results": [],
        }


def fetch_url(url: str, timeout: int = 30) -> dict[str, Any]:
    """Fetch content from a URL and convert HTML to markdown format.
    
    This tool fetches web page content and converts it to clean markdown text.
    
    Args:
        url: The URL to fetch (must be a valid HTTP/HTTPS URL)
        timeout: Request timeout in seconds (default: 30)
        
    Returns:
        Dictionary containing:
        - success: Whether the request succeeded
        - url: The final URL after redirects
        - markdown_content: The page content converted to markdown
        - status_code: HTTP status code
        - content_length: Length of the content in characters
        - error: If an error occurred
        
    Example:
        >>> result = fetch_url("https://example.com")
        >>> print(result["markdown_content"][:200])
    """
    try:
        import requests
        from markdownify import markdownify
    except ImportError as e:
        return {
            "error": f"Required package not installed: {e.name}. Install with: pip install requests markdownify",
            "url": url,
        }
    
    # Validate URL scheme
    if not url.startswith(("http://", "https://")):
        return {
            "error": "URL must start with http:// or https://",
            "url": url,
        }
    
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; DeepAgents/1.0)"},
        )
        response.raise_for_status()
        
        # Convert HTML content to markdown
        markdown_content = markdownify(response.text)
        
        return {
            "success": True,
            "url": str(response.url),
            "markdown_content": markdown_content,
            "status_code": response.status_code,
            "content_length": len(markdown_content),
        }
        
    except requests.exceptions.Timeout:
        return {
            "error": f"Request timed out after {timeout} seconds",
            "url": url,
        }
    except requests.exceptions.RequestException as e:
        return {
            "error": f"Fetch URL error: {str(e)}",
            "url": url,
        }
    except Exception as e:
        return {
            "error": f"Error converting HTML to markdown: {str(e)}",
            "url": url,
        }


def duckduckgo_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search the web using DuckDuckGo (free alternative to Tavily).
    
    This is a free alternative when Tavily API is not available.
    
    Args:
        query: The search query
        max_results: Number of results to return (default: 5)
        
    Returns:
        Dictionary containing search results with title, url, and snippet
    """
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return {
            "error": "duckduckgo_search package not installed. Install with: pip install duckduckgo-search",
            "query": query,
        }
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            
        formatted_results = []
        for r in results:
            formatted_results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "content": r.get("body", ""),
            })
        
        return {
            "query": query,
            "results": formatted_results,
        }
        
    except Exception as e:
        return {
            "error": f"DuckDuckGo search error: {str(e)}",
            "query": query,
            "results": [],
        }
