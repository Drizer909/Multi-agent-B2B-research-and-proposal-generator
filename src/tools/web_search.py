"""
Web Search Tool — Tavily integration for real-time company research.

Used by the Research Agent to find:
- Company information
- Recent news
- Industry data
- Competitor analysis

Uses Tavily's FREE tier (1,000 searches/month).
"""

from langchain_core.tools import tool
from tavily import TavilyClient

from src.config import APIKeys, OpenRouterRateLimiter

# Initialize a rate limiter instance if not already provided in config
rate_limiter = OpenRouterRateLimiter()

@tool
def web_search(query: str) -> str:
    """
    Search the web for real-time information about a company or topic.

    Use this tool to find:
    - Company overview, size, and industry
    - Recent news and press releases
    - Competitor information
    - Technology stack details
    - Funding and growth signals

    Args:
        query: A specific search query (e.g., "Stripe company overview 2024")

    Returns:
        A formatted string with search results including titles, URLs, and content.
    """
    try:
        api_key = APIKeys.require_tavily()
        client = TavilyClient(api_key=api_key)

        # Rate limit to be respectful of free tier
        rate_limiter.wait_if_needed()

        response = client.search(
            query=query,
            search_depth="basic",       # "basic" is free, "advanced" costs more
            max_results=5,
            include_answer=True,        # Get a synthesized answer
            include_raw_content=False,  # Save tokens
        )

        # Format results for the LLM
        output_parts = []

        # Include the synthesized answer if available
        if response.get("answer"):
            output_parts.append(f"📋 Summary: {response['answer']}\n")

        # Include individual results
        output_parts.append("🔍 Sources:")
        for i, result in enumerate(response.get("results", []), 1):
            title = result.get("title", "No title")
            url = result.get("url", "")
            content = result.get("content", "")[:300]  # Truncate to save tokens
            output_parts.append(f"\n  {i}. {title}")
            output_parts.append(f"     URL: {url}")
            output_parts.append(f"     {content}")

        return "\n".join(output_parts)

    except ValueError as e:
        # API key not configured
        return f"⚠️ Web search unavailable: {e}"
    except Exception as e:
        return f"❌ Web search error: {e}"


@tool
def web_search_news(query: str) -> str:
    """
    Search for recent news about a company or topic.

    Use this tool specifically for:
    - Recent company news and announcements
    - Industry trends
    - Funding rounds
    - Product launches

    Args:
        query: A specific news search query (e.g., "Stripe recent news funding")

    Returns:
        A formatted string with recent news results.
    """
    try:
        api_key = APIKeys.require_tavily()
        client = TavilyClient(api_key=api_key)

        rate_limiter.wait_if_needed()

        response = client.search(
            query=query,
            search_depth="basic",
            max_results=5,
            topic="news",  # Focus on news results
            days=90,       # Last 90 days
            include_answer=True,
        )

        output_parts = []

        if response.get("answer"):
            output_parts.append(f"📰 News Summary: {response['answer']}\n")

        output_parts.append("📰 Recent Articles:")
        for i, result in enumerate(response.get("results", []), 1):
            title = result.get("title", "No title")
            url = result.get("url", "")
            content = result.get("content", "")[:200]
            published = result.get("published_date", "Unknown date")
            output_parts.append(f"\n  {i}. [{published}] {title}")
            output_parts.append(f"     URL: {url}")
            output_parts.append(f"     {content}")

        return "\n".join(output_parts)

    except ValueError as e:
        return f"⚠️ News search unavailable: {e}"
    except Exception as e:
        return f"❌ News search error: {e}"