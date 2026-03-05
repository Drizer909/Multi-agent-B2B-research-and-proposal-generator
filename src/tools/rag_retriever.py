"""
RAG Search Tools — ChromaDB retrieval for internal knowledge base.

Used by agents to find:
- Relevant case studies
- Product documentation
- Proposal templates

These tools wrap the retriever.py functions with @tool decorators
so LangGraph agents can call them.
"""

from langchain_core.tools import tool

from src.rag.retriever import (
    search_case_studies,
    search_product_docs,
    search_with_filters,
)


@tool
def rag_search(query: str) -> str:
    """
    Search the internal knowledge base for relevant information.

    This searches ALL documents: case studies, product docs, and templates.
    Use this for general queries about our company's offerings.

    Args:
        query: A natural language query (e.g., "solutions for SaaS churn reduction")

    Returns:
        Formatted results from the knowledge base with source attribution.
    """
    try:
        results = search_with_filters(query=query, k=5)

        if not results:
            return "No relevant documents found in the knowledge base."

        output_parts = ["📚 Knowledge Base Results:\n"]

        for i, doc in enumerate(results, 1):
            source = doc.metadata.get("filename", "unknown")
            doc_type = doc.metadata.get("doc_type", "unknown")
            industry = doc.metadata.get("industry", "N/A")
            content = doc.page_content[:500]

            output_parts.append(f"  {i}. [{doc_type}] {source}")
            output_parts.append(f"     Industry: {industry}")
            output_parts.append(f"     Content: {content}")
            output_parts.append("")

        return "\n".join(output_parts)

    except Exception as e:
        return f"❌ RAG search error: {e}"


@tool
def rag_search_case_studies(query: str, industry: str = "") -> str:
    """
    Search for relevant case studies in our knowledge base.

    Use this to find past success stories that match a prospect's situation.

    Args:
        query: What kind of case study to find (e.g., "churn reduction for SaaS")
        industry: Optional industry filter (e.g., "SaaS", "fintech", "healthcare")

    Returns:
        Matching case studies with details and results.
    """
    try:
        results = search_case_studies(
            query=query,
            industry=industry if industry else None,
            k=5,
        )

        if not results:
            return f"No case studies found matching '{query}'" + (
                f" in {industry}" if industry else ""
            )

        output_parts = ["📊 Relevant Case Studies:\n"]

        for i, doc in enumerate(results, 1):
            source = doc.metadata.get("filename", "unknown")
            ind = doc.metadata.get("industry", "N/A")
            pain = doc.metadata.get("pain_point", "N/A")
            content = doc.page_content[:600]

            output_parts.append(f"  {i}. {source}")
            output_parts.append(f"     Industry: {ind}")
            output_parts.append(f"     Pain Point: {pain}")
            output_parts.append(f"     Details: {content}")
            output_parts.append("")

        return "\n".join(output_parts)

    except Exception as e:
        return f"❌ Case study search error: {e}"


@tool
def rag_search_product_docs(query: str) -> str:
    """
    Search our product documentation for features, pricing, and capabilities.

    Use this to find:
    - Platform features and capabilities
    - Pricing tiers and packages
    - Technical specifications
    - Integration details

    Args:
        query: What product information to find (e.g., "enterprise pricing tier")

    Returns:
        Matching product documentation excerpts.
    """
    try:
        results = search_product_docs(query=query, k=5)

        if not results:
            return f"No product docs found matching '{query}'"

        output_parts = ["📄 Product Documentation:\n"]

        for i, doc in enumerate(results, 1):
            source = doc.metadata.get("filename", "unknown")
            content = doc.page_content[:600]

            output_parts.append(f"  {i}. {source}")
            output_parts.append(f"     {content}")
            output_parts.append("")

        return "\n".join(output_parts)

    except Exception as e:
        return f"❌ Product doc search error: {e}"