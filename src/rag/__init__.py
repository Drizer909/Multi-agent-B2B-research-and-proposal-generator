"""RAG pipeline for the B2B Proposal Generator."""

from src.rag.embeddings import get_vector_store, get_or_create_collection
from src.rag.ingest import ingest_documents
from src.rag.retriever import (
    get_retriever,
    search_with_filters,
    search_case_studies,
    search_product_docs,
)

__all__ = [
    "get_vector_store",
    "get_or_create_collection",
    "ingest_documents",
    "get_retriever",
    "search_with_filters",
    "search_case_studies",
    "search_product_docs",
]
