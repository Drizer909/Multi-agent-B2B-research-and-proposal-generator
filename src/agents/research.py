"""
Research Agent — Gathers comprehensive intelligence about a prospect company.

This agent uses web search + RAG tools to build a complete company profile.
It writes structured data into ProposalState.research_data.

Flow:
    1. Receives company_name and user_request from state
    2. Calls web_search and web_search_news for real-time data
    3. Calls rag_search for internal knowledge
    4. Uses LLM to synthesize into structured ResearchData
    5. Returns updated state with research_data, industry, pain_points
"""

import json
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import ModelConfig, OpenRouterRateLimiter
from src.state.schema import ProposalState, ResearchData
from src.tools.web_search import web_search, web_search_news
from src.tools.rag_search import rag_search

# Initialize rate limiter
rate_limiter = OpenRouterRateLimiter()

# ──────────────────────────────────────────────
# System Prompt
# ──────────────────────────────────────────────

RESEARCH_SYSTEM_PROMPT = """You are an expert B2B research analyst. Your job is to gather comprehensive intelligence about a prospect company to help create a winning business proposal.

RESEARCH OBJECTIVES:
1. Company overview (what they do, their market position)
2. Industry classification
3. Company size (employees, revenue if available)
4. Headquarters location
5. Key challenges and pain points they're likely facing
6. Recent news and developments
7. Competitors
8. Technologies they use
9. Growth signals (hiring, funding, expansion)
10. Risk factors

TOOL USAGE:
- Use web_search for company information, competitors, and technology stack
- Use web_search_news for recent developments and news
- Use rag_search to find relevant internal knowledge about their industry

OUTPUT FORMAT:
You MUST return your findings as a valid JSON object with this exact structure:
{
    "company_overview": "2-3 sentence overview",
    "industry": "Primary industry (e.g., SaaS, FinTech, Healthcare)",
    "employee_count": "Approximate number or range",
    "headquarters": "City, State/Country",
    "founded_year": "Year or 'Unknown'",
    "recent_news": ["news item 1", "news item 2"],
    "competitors": ["competitor 1", "competitor 2"],
    "technologies_used": ["tech 1", "tech 2"],
    "funding_info": "Latest funding details or 'Not available'",
    "key_challenges": ["challenge 1", "challenge 2"],
    "growth_signals": ["signal 1", "signal 2"],
    "risk_factors": ["risk 1", "risk 2"],
    "sources": ["source URL 1", "source URL 2"]
}

Be thorough but concise. Focus on information relevant to creating a business proposal."""


# ──────────────────────────────────────────────
# Tool Execution Helper
# ──────────────────────────────────────────────

def _execute_research_tools(company_name: str, user_request: str) -> str:
    """
    Run all research tools and combine results.

    This is a sequential approach (not agentic tool-calling) to be
    predictable and conserve API calls on the free tier.
    """
    results = []

    # 1. General company search
    print("  🔍 Searching web for company info...")
    try:
        company_info = web_search.invoke(f"{company_name} company overview business")
        results.append(f"=== COMPANY INFO ===\n{company_info}")
    except Exception as e:
        results.append(f"=== COMPANY INFO ===\nSearch failed: {e}")

    # 2. Recent news
    print("  📰 Searching for recent news...")
    try:
        news = web_search_news.invoke(f"{company_name} recent news announcements")
        results.append(f"\n=== RECENT NEWS ===\n{news}")
    except Exception as e:
        results.append(f"\n=== RECENT NEWS ===\nNews search failed: {e}")

    # 3. Competitors and industry
    print("  🏢 Searching for competitors...")
    try:
        competitors = web_search.invoke(f"{company_name} competitors market landscape")
        results.append(f"\n=== COMPETITORS ===\n{competitors}")
    except Exception as e:
        results.append(f"\n=== COMPETITORS ===\nSearch failed: {e}")

    # 4. Internal knowledge base
    print("  📚 Searching internal knowledge base...")
    try:
        internal = rag_search.invoke(f"{company_name} {user_request}")
        results.append(f"\n=== INTERNAL KNOWLEDGE ===\n{internal}")
    except Exception as e:
        results.append(f"\n=== INTERNAL KNOWLEDGE ===\nRAG search failed: {e}")

    return "\n".join(results)


# ──────────────────────────────────────────────
# Main Agent Function (LangGraph Node)
# ──────────────────────────────────────────────

def research_agent(state: ProposalState) -> dict:
    """
    Research Agent — LangGraph node function.

    Reads:  company_name, user_request
    Writes: research_data, industry, company_size, pain_points, current_phase
    """
    company_name = state.get("company_name", "")
    user_request = state.get("user_request", "")

    print("\n" + "=" * 60)
    print("  🔬 RESEARCH AGENT — Starting")
    print(f"  Company: {company_name}")
    print("=" * 60)

    try:
        # Step 1: Gather raw research data from tools
        print("\n📡 Phase 1: Gathering data from tools...")
        raw_research = _execute_research_tools(company_name, user_request)

        # Step 2: Use LLM to synthesize into structured format
        print("\n🧠 Phase 2: Synthesizing with LLM...")
        llm = ModelConfig.get_llm()
        rate_limiter.wait_if_needed()

        messages = [
            SystemMessage(content=RESEARCH_SYSTEM_PROMPT),
            HumanMessage(content=(
                f"Research the following company and return a JSON object with your findings.\n\n"
                f"Company: {company_name}\n"
                f"Request Context: {user_request}\n\n"
                f"Here is the raw data I've gathered from various sources:\n\n"
                f"{raw_research}\n\n"
                f"Synthesize this into the required JSON format. "
                f"If information is missing, make reasonable inferences based on "
                f"available data or mark as 'Not available'.\n\n"
                f"Return ONLY the JSON object, no other text."
            )),
        ]

        response = llm.invoke(messages)
        response_text = response.content.strip()

        # Step 3: Parse the JSON response
        print("\n📝 Phase 3: Parsing structured output...")

        # Clean up response (remove markdown code fences if present)
        cleaned_text = response_text
        if "```" in cleaned_text:
            # Extract content between triple backticks
            import re
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned_text, re.DOTALL)
            if match:
                cleaned_text = match.group(1)
        
        cleaned_text = cleaned_text.strip()

        try:
            research_data: ResearchData = json.loads(cleaned_text)
        except json.JSONDecodeError:
            # Fallback: try to find anything that looks like a JSON object
            import re
            match = re.search(r"\{.*\}", cleaned_text, re.DOTALL)
            if match:
                research_data = json.loads(match.group(0))
            else:
                raise

        # Extract key fields for state
        industry = research_data.get("industry", "Unknown")
        company_size = research_data.get("employee_count", "Unknown")
        pain_points = research_data.get("key_challenges", [])

        print(f"\n  ✅ Industry: {industry}")
        print(f"  ✅ Company Size: {company_size}")
        print(f"  ✅ Pain Points Found: {len(pain_points)}")
        for i, pp in enumerate(pain_points, 1):
            print(f"     {i}. {pp}")

        print("\n" + "=" * 60)
        print("  🔬 RESEARCH AGENT — Complete ✅")
        print("=" * 60)

        return {
            "research_data": research_data,
            "industry": industry,
            "company_size": company_size,
            "pain_points": pain_points,
            "current_phase": "research_complete",
        }

    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse research data as JSON: {e}"
        print(f"\n  ❌ {error_msg}")
        return {
            "research_data": {},
            "current_phase": "research_failed",
            "error": error_msg,
        }
    except Exception as e:
        error_msg = f"Research agent error: {e}"
        print(f"\n  ❌ {error_msg}")
        return {
            "research_data": {},
            "current_phase": "research_failed",
            "error": error_msg,
        }