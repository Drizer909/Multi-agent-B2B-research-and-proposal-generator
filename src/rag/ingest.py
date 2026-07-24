"""
Document ingestion pipeline for the RAG system.

Scans data directories, extracts metadata from markdown headers,
chunks documents, and stores embeddings in ChromaDB.

Usage:
    python -m src.rag.ingest
"""

import fcntl
import hashlib
import re
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import ModelConfig, RAGConfig, StorageConfig
from src.rag.embeddings import get_vector_store


# ──────────────────────────────────────────────
# Metadata Extraction
# ──────────────────────────────────────────────

def extract_metadata(text: str, file_path: Path) -> dict:
    """
    Parse markdown headers to extract structured metadata.

    Looks for:
      ## Industry → metadata["industry"]
      ## Company Size → metadata["company_size"]
      ## Pain Point → metadata["pain_point"]

    Also sets doc_type based on the parent directory name.
    """
    metadata: dict = {
        "source": str(file_path),
        "filename": file_path.name,
    }

    # Determine doc_type from directory
    parent = file_path.parent.name
    doc_type_map = {
        "case_studies": "case_study",
        "product_docs": "product_doc",
        "templates": "template",
    }
    metadata["doc_type"] = doc_type_map.get(parent, "unknown")

    # Extract structured fields from ## headers
    header_patterns = {
        "industry": r"##\s*Industry\s*\n+(.+?)(?:\n#|\n\n|\Z)",
        "company_size": r"##\s*Company Size\s*\n+(.+?)(?:\n#|\n\n|\Z)",
        "pain_point": r"##\s*Pain Point\s*\n+(.+?)(?:\n#|\n\n|\Z)",
    }

    for field, pattern in header_patterns.items():
        match = re.search(pattern, text, re.DOTALL)
        if match:
            metadata[field] = match.group(1).strip()

    return metadata


# ──────────────────────────────────────────────
# Directory Scanning
# ──────────────────────────────────────────────

def scan_data_directories() -> list[dict]:
    """
    Walk through data directories and load all .md files.

    Returns a list of dicts with keys: text, metadata, path.
    """
    directories = [
        StorageConfig.CASE_STUDIES_DIR,
        StorageConfig.PRODUCT_DOCS_DIR,
        StorageConfig.TEMPLATES_DIR,
    ]

    documents = []
    for directory in directories:
        if not directory.exists():
            print(f"  ⚠️  Directory not found: {directory}")
            continue

        for md_file in sorted(directory.glob("*.md")):
            text = md_file.read_text(encoding="utf-8").strip()
            if not text:
                print(f"  ⚠️  Empty file, skipping: {md_file.name}")
                continue

            metadata = extract_metadata(text, md_file)
            print(f"  📄 Loaded: {md_file.parent.name}/{md_file.name} ({len(text):,} chars)")
            documents.append({
                "text": text,
                "metadata": metadata,
                "path": md_file,
            })

    return documents


# ──────────────────────────────────────────────
# Main Ingestion Function
# ──────────────────────────────────────────────

def ingest_documents(vector_store=None) -> int:
    """
    Full ingestion pipeline:
    1. Scan data directories for .md files
    2. Extract metadata from markdown headers
    3. Chunk documents using RecursiveCharacterTextSplitter
    4. Embed and store in ChromaDB

    Returns the number of chunks stored.
    """
    print("\n📥 Starting document ingestion...")
    print("=" * 55)

    # Step 1: Scan and load documents
    print("\n📂 Step 1: Scanning data directories...")
    documents = scan_data_directories()

    if not documents:
        print("  ❌ No documents found! Add .md files to data/ directories.")
        return 0

    print(f"\n  ✅ Found {len(documents)} documents")

    # Step 2: Chunk documents
    print(f"\n✂️  Step 2: Chunking (size={RAGConfig.CHUNK_SIZE}, overlap={RAGConfig.CHUNK_OVERLAP})...")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=RAGConfig.CHUNK_SIZE,
        chunk_overlap=RAGConfig.CHUNK_OVERLAP,
        length_function=len,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""],
    )

    all_texts = []
    all_metadatas = []

    for doc in documents:
        chunks = text_splitter.split_text(doc["text"])
        for i, chunk in enumerate(chunks):
            chunk_metadata = {**doc["metadata"], "chunk_index": i}
            all_texts.append(chunk)
            all_metadatas.append(chunk_metadata)

    print(f"  ✅ Created {len(all_texts)} chunks from {len(documents)} documents")

    # Step 3: Clear existing collection and store
    print("\n💾 Step 3: Embedding and storing in ChromaDB...")

    vector_store = vector_store or get_vector_store()

    # Clear existing data to avoid duplicates on re-ingestion
    existing = vector_store.get()
    if existing and existing["ids"]:
        print(f"  🗑️  Clearing {len(existing['ids'])} existing chunks...")
        vector_store.delete(ids=existing["ids"])

    # Add new documents
    vector_store.add_texts(
        texts=all_texts,
        metadatas=all_metadatas,
    )

    print(f"  ✅ Stored {len(all_texts)} chunks in ChromaDB")
    print(f"  📁 Persist dir: {StorageConfig.CHROMA_PERSIST_DIR}")
    print(f"  📚 Collection: {RAGConfig.COLLECTION_NAME}")

    # Summary
    print("\n" + "=" * 55)
    print("  INGESTION SUMMARY")
    print("=" * 55)

    doc_types = {}
    for m in all_metadatas:
        dt = m.get("doc_type", "unknown")
        doc_types[dt] = doc_types.get(dt, 0) + 1

    for dt, count in sorted(doc_types.items()):
        print(f"  {dt:20s} → {count} chunks")

    print(f"\n  Total chunks: {len(all_texts)}")
    print("=" * 55)

    return len(all_texts)


def _corpus_fingerprint() -> str:
    """Hash source documents and embedding/chunk settings that shape the index."""
    digest = hashlib.sha256()
    settings = (
        ModelConfig.EMBEDDING_MODEL,
        ModelConfig.EMBEDDING_MODEL_REVISION,
        str(RAGConfig.CHUNK_SIZE),
        str(RAGConfig.CHUNK_OVERLAP),
        RAGConfig.COLLECTION_NAME,
    )
    digest.update("\0".join(settings).encode("utf-8"))

    for path in sorted(StorageConfig.DATA_DIR.rglob("*.md")):
        digest.update(str(path.relative_to(StorageConfig.DATA_DIR)).encode("utf-8"))
        digest.update(path.read_bytes())

    return digest.hexdigest()


def ensure_documents_ingested() -> int:
    """Create or refresh the index under a cross-process filesystem lock."""
    lock_path = StorageConfig.STORAGE_DIR / ".rag-ingest.lock"
    fingerprint_path = Path(StorageConfig.CHROMA_PERSIST_DIR) / ".corpus.sha256"
    expected_fingerprint = _corpus_fingerprint()

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

        vector_store = get_vector_store()
        existing = vector_store.get(include=[])
        existing_count = len(existing.get("ids", [])) if existing else 0
        current_fingerprint = (
            fingerprint_path.read_text(encoding="utf-8").strip()
            if fingerprint_path.is_file()
            else ""
        )

        if existing_count and current_fingerprint == expected_fingerprint:
            print(f"  Knowledge base already contains {existing_count} current chunks")
            return existing_count

        if existing_count:
            print("  Knowledge base sources changed; rebuilding the index")
        fingerprint_path.unlink(missing_ok=True)
        count = ingest_documents(vector_store=vector_store)
        if count:
            fingerprint_path.write_text(expected_fingerprint, encoding="utf-8")
        return count


# ──────────────────────────────────────────────
# Standalone entry point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    count = ingest_documents()
    if count > 0:
        print(f"\n🎉 Ingestion complete! {count} chunks ready for retrieval.")
    else:
        print("\n❌ Ingestion failed — no chunks were stored.")
