"""
Embedding & Vector Store initialization.

Creates a ChromaDB vector store backed by HuggingFace embeddings.
All settings are pulled from src.config (ModelConfig, StorageConfig, RAGConfig).
"""

from langchain_chroma import Chroma

from src.config import ModelConfig, RAGConfig, StorageConfig


def get_vector_store() -> Chroma:
    """
    Return a LangChain Chroma vector store, ready for reads and writes.

    Uses:
    - HuggingFace all-MiniLM-L6-v2 embeddings (local, free)
    - ChromaDB persisted to StorageConfig.CHROMA_PERSIST_DIR
    - Collection name from RAGConfig.COLLECTION_NAME
    """
    embeddings = ModelConfig.get_embeddings()

    vector_store = Chroma(
        collection_name=RAGConfig.COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=StorageConfig.CHROMA_PERSIST_DIR,
    )

    return vector_store


def get_or_create_collection() -> Chroma:
    """Alias for get_vector_store (creates collection on first use)."""
    return get_vector_store()
