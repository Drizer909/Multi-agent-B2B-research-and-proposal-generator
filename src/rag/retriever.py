"""
Retriever with metadata filtering for the RAG pipeline.

Provides LangChain-compatible retriever and convenience functions
for searching case studies and product docs with metadata filters.
"""

from typing import Optional

from langchain_core.documents import Document

from src.config import RAGConfig
from src.rag.embeddings import get_vector_store


def get_retriever():
    """
    Return a LangChain-compatible retriever.

    Settings from RAGConfig:
    - top-k: SEARCH_K (5)
    - score threshold: SCORE_THRESHOLD (0.3)
    """
    vector_store = get_vector_store()

    return vector_store.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "k": RAGConfig.SEARCH_K,
            "score_threshold": RAGConfig.SCORE_THRESHOLD,
        },
    )


def search_with_filters(
    query: str,
    doc_type: Optional[str] = None,
    industry: Optional[str] = None,
    company_size: Optional[str] = None,
    k: Optional[int] = None,
) -> list[Document]:
    """
    Search ChromaDB with optional metadata filters.

    Filters use AND logic — all specified filters must match.

    Args:
        query: Natural language search query
        doc_type: Filter by type ("case_study", "product_doc", "template")
        industry: Filter by industry (partial match via $contains)
        company_size: Filter by company size (partial match via $contains)
        k: Number of results (default: RAGConfig.SEARCH_K)

    Returns:
        List of matching LangChain Document objects
    """
    vector_store = get_vector_store()
    k = k or RAGConfig.SEARCH_K
    
    # doc_type is a hard filter (efficient in DB)
    where_filter = None
    if doc_type:
        where_filter = {"doc_type": {"$eq": doc_type}}

    # We fetch more results than requested to allow for Python-side filtering
    # of industry and company_size (as Chroma doesn't support easy substring match in where)
    fetch_k = k * 4 if (industry or company_size) else k
    
    results = vector_store.similarity_search(
        query=query,
        k=fetch_k,
        filter=where_filter,
    )

    # Python-side filtering for flexibility
    filtered_results = []
    for doc in results:
        match = True
        
        if industry:
            doc_ind = doc.metadata.get("industry", "").lower()
            if industry.lower() not in doc_ind:
                match = False
        
        if company_size:
            doc_size = doc.metadata.get("company_size", "").lower()
            if company_size.lower() not in doc_size:
                match = False
                
        if match:
            filtered_results.append(doc)
            if len(filtered_results) >= k:
                break
                
    return filtered_results


def search_case_studies(
    query: str,
    industry: Optional[str] = None,
    k: Optional[int] = None,
) -> list[Document]:
    """
    Convenience: search only case study documents.

    Args:
        query: Natural language search query
        industry: Optionally filter by industry
        k: Number of results
    """
    return search_with_filters(
        query=query,
        doc_type="case_study",
        industry=industry,
        k=k,
    )


def search_product_docs(
    query: str,
    k: Optional[int] = None,
) -> list[Document]:
    """
    Convenience: search only product documentation.

    Args:
        query: Natural language search query
        k: Number of results
    """
    return search_with_filters(
        query=query,
        doc_type="product_doc",
        k=k,
    )
