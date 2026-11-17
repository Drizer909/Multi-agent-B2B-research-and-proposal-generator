"""Index the repository's Markdown documents in ChromaDB."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.ingest import ingest_documents


if __name__ == "__main__":
    sys.exit(0 if ingest_documents() else 1)
