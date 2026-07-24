"""
Central configuration for the B2B Proposal Generator.

LLM:        Meta Llama 3.3 70B Instruct (FREE) via OpenRouter
Embeddings: HuggingFace all-MiniLM-L6-v2 (FREE, local)
Search:     Tavily (FREE tier)
Vector DB:  ChromaDB (local)

OpenRouter uses an OpenAI-compatible API, so we use LangChain's
ChatOpenAI class with base_url="https://openrouter.ai/api/v1"
"""

import os
import warnings
from pathlib import Path

from dotenv import load_dotenv

# Suppress urllib3 SSL warnings and HuggingFace Hub unauthenticated warnings
try:
    import urllib3
    from urllib3.exceptions import NotOpenSSLWarning
    warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
    warnings.filterwarnings("ignore", message=".*unauthenticated requests to the HF Hub.*")
except ImportError:
    pass

# ──────────────────────────────────────────────
# Load .env file from project root
# ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)


def _resolve_path(value: str | Path) -> Path:
    """Resolve relative deployment paths from the project root."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


# ──────────────────────────────────────────────
# API Keys
# ──────────────────────────────────────────────
class APIKeys:
    """All external API keys."""

    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")

    @classmethod
    def validate(cls) -> dict[str, bool]:
        """Check which API keys are configured."""
        return {
            "openrouter": bool(
                cls.OPENROUTER_API_KEY
                and not cls.OPENROUTER_API_KEY.startswith("sk-or-v1-your")
            ),
            "tavily": bool(
                cls.TAVILY_API_KEY
                and not cls.TAVILY_API_KEY.startswith("tvly-your")
            ),
            "langsmith": bool(cls.LANGCHAIN_API_KEY),
        }

    @classmethod
    def require_openrouter(cls) -> str:
        """Get OpenRouter key or raise clear error."""
        if not cls.OPENROUTER_API_KEY or cls.OPENROUTER_API_KEY.startswith("sk-or-v1-your"):
            raise ValueError(
                "\n❌ OPENROUTER_API_KEY not set!\n"
                "   1. Go to https://openrouter.ai\n"
                "   2. Sign up (FREE — no credit card needed)\n"
                "   3. Go to https://openrouter.ai/settings/keys\n"
                "   4. Create an API key\n"
                "   5. Add it to your .env file as OPENROUTER_API_KEY=sk-or-v1-...\n"
            )
        return cls.OPENROUTER_API_KEY

    @classmethod
    def require_tavily(cls) -> str:
        """Get Tavily key or raise clear error."""
        if not cls.TAVILY_API_KEY or cls.TAVILY_API_KEY.startswith("tvly-your"):
            raise ValueError(
                "\n❌ TAVILY_API_KEY not set!\n"
                "   1. Go to https://tavily.com\n"
                "   2. Sign up (FREE tier available)\n"
                "   3. Add the key to your .env file\n"
            )
        return cls.TAVILY_API_KEY


# ──────────────────────────────────────────────
# Model Configuration
# ──────────────────────────────────────────────
class ModelConfig:
    """LLM and embedding model settings."""

    # ─── LLM: Llama 3.3 70B via OpenRouter ───
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openrouter")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    LLM_MAX_TOKENS: int = 4096
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")

    # OpenRouter free tier rate limits
    # ~20 requests/minute, 200 requests/day for free models
    OPENROUTER_RATE_LIMIT_RPM: int = 20
    OPENROUTER_RATE_LIMIT_RPD: int = 200

    # ─── Embeddings: HuggingFace (local, free) ───
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "huggingface")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    EMBEDDING_MODEL_REVISION: str = os.getenv(
        "EMBEDDING_MODEL_REVISION",
        "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
    )
    EMBEDDING_DIMENSIONS: int = 384  # all-MiniLM-L6-v2 outputs 384-dim vectors

    @classmethod
    def get_llm(cls):
        """
        Create and return the LLM instance.

        Uses LangChain's ChatOpenAI with OpenRouter's base_url.
        OpenRouter is OpenAI-API-compatible, so ChatOpenAI works perfectly.

        This is the KEY TRICK:
            ChatOpenAI(base_url="https://openrouter.ai/api/v1")
        tells LangChain to send requests to OpenRouter instead of OpenAI.
        """
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=cls.LLM_MODEL,
            temperature=cls.LLM_TEMPERATURE,
            max_tokens=cls.LLM_MAX_TOKENS,
            api_key=APIKeys.require_openrouter(),
            base_url=cls.LLM_BASE_URL,
            default_headers={
                "HTTP-Referer": "https://b2b-proposal-generator.app",
                "X-Title": "B2B Proposal Generator",
            },
        )

    @classmethod
    def get_embeddings(cls):
        """
        Create and return the embedding model.

        Runs LOCALLY on your Mac via HuggingFace.
        First call downloads the model (~90MB), subsequent calls use cache.
        No API key needed. Completely free.
        """
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(
            model_name=cls.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu", "revision": cls.EMBEDDING_MODEL_REVISION},
            encode_kwargs={"normalize_embeddings": True},
        )


# ──────────────────────────────────────────────
# Runtime / Deployment Configuration
# ──────────────────────────────────────────────
class RuntimeConfig:
    """Production server and deployment settings."""

    AUTO_INGEST: bool = _env_bool("AUTO_INGEST", True)
    FRONTEND_STATIC_DIR: Path = _resolve_path(
        os.getenv("FRONTEND_STATIC_DIR", str(PROJECT_ROOT / "frontend" / "out"))
    )
    CORS_ORIGINS: tuple[str, ...] = tuple(
        origin.strip().rstrip("/")
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    )


# ──────────────────────────────────────────────
# Database / Storage Paths
# ──────────────────────────────────────────────
_CONFIGURED_STORAGE_DIR = os.getenv("STORAGE_DIR")
_DEFAULT_STORAGE_DIR = _resolve_path(_CONFIGURED_STORAGE_DIR or "storage")


def _storage_path(env_name: str, storage_name: str, legacy_name: str) -> Path:
    """Use explicit paths first and preserve legacy defaults during upgrades."""
    configured = os.getenv(env_name)
    if configured:
        return _resolve_path(configured)

    legacy_path = PROJECT_ROOT / legacy_name
    if _CONFIGURED_STORAGE_DIR is None and legacy_path.exists():
        return legacy_path

    return _DEFAULT_STORAGE_DIR / storage_name


class StorageConfig:
    """Persistent file paths, all configurable from one storage root."""

    STORAGE_DIR: Path = _DEFAULT_STORAGE_DIR
    CHROMA_PERSIST_DIR: str = str(
        _storage_path("CHROMA_PERSIST_DIR", "chroma_db", "chroma_db")
    )
    SQLITE_CHECKPOINT_PATH: str = str(
        _storage_path("SQLITE_CHECKPOINT_PATH", "checkpoints.db", "checkpoints.db")
    )
    OUTPUT_DIR: Path = _storage_path("OUTPUT_DIR", "output", "output")

    DATA_DIR: Path = PROJECT_ROOT / "data"
    CASE_STUDIES_DIR: Path = DATA_DIR / "case_studies"
    PRODUCT_DOCS_DIR: Path = DATA_DIR / "product_docs"
    TEMPLATES_DIR: Path = DATA_DIR / "templates"

    @classmethod
    def ensure_directories(cls) -> None:
        """Create all required writable directories if they do not exist."""
        for dir_path in [
            cls.STORAGE_DIR,
            Path(cls.CHROMA_PERSIST_DIR),
            Path(cls.SQLITE_CHECKPOINT_PATH).parent,
            cls.OUTPUT_DIR,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────
# RAG Configuration
# ──────────────────────────────────────────────
class RAGConfig:
    """Settings for the RAG pipeline."""

    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    SEARCH_K: int = 5
    SCORE_THRESHOLD: float = 0.3
    COLLECTION_NAME: str = "b2b_knowledge_base"


# ──────────────────────────────────────────────
# Proposal Configuration
# ──────────────────────────────────────────────
class ProposalConfig:
    """Settings for proposal generation."""

    QA_AUTO_PASS_SCORE: float = 0.9
    QA_AUTO_RETRY_SCORE: float = 0.6
    MAX_REVISIONS: int = 3

    SECTIONS: list[str] = [
        "Executive Summary",
        "Understanding Your Challenges",
        "Our Proposed Solution",
        "Relevant Case Studies & Results",
        "Implementation Timeline",
        "Investment & ROI",
        "Next Steps",
    ]

    YOUR_COMPANY_NAME: str = "NexusAI Solutions"
    YOUR_COMPANY_TAGLINE: str = "AI-Powered Business Transformation"


# ──────────────────────────────────────────────
# OpenRouter Rate Limiter
# ──────────────────────────────────────────────
class OpenRouterRateLimiter:
    """
    Simple rate limiter for OpenRouter's free tier.

    Free tier limits (approximate):
    - ~20 requests per minute
    - ~200 requests per day

    Usage:
        limiter = OpenRouterRateLimiter()
        limiter.wait_if_needed()  # Call before each LLM call
    """

    def __init__(self):
        self._request_times: list[float] = []
        self._daily_count: int = 0

    def wait_if_needed(self) -> None:
        """Synchronous rate limit check with sleep if needed."""
        import time

        now = time.time()

        # Remove requests older than 60 seconds
        self._request_times = [t for t in self._request_times if now - t < 60]

        # If at limit, wait until oldest request expires
        if len(self._request_times) >= ModelConfig.OPENROUTER_RATE_LIMIT_RPM:
            sleep_time = 60 - (now - self._request_times[0]) + 1.0
            if sleep_time > 0:
                print(f"  ⏳ Rate limit reached. Waiting {sleep_time:.1f}s...")
                time.sleep(sleep_time)

        self._request_times.append(time.time())
        self._daily_count += 1

    @property
    def requests_remaining_today(self) -> int:
        return max(0, ModelConfig.OPENROUTER_RATE_LIMIT_RPD - self._daily_count)


# Global rate limiter instance (shared across all agents)
rate_limiter = OpenRouterRateLimiter()


# ──────────────────────────────────────────────
# Print config status
# ──────────────────────────────────────────────
def print_config_status() -> None:
    """Print the current configuration status."""
    keys = APIKeys.validate()

    print("=" * 60)
    print("  B2B PROPOSAL GENERATOR — Configuration Status")
    print("  Stack: Llama 3.3 70B (OpenRouter) + HuggingFace Embeddings")
    print("=" * 60)
    print()
    print("  🤖 LLM Setup:")
    print(f"    Provider     → OpenRouter (FREE)")
    print(f"    Model        → {ModelConfig.LLM_MODEL}")
    print(f"    Base URL     → {ModelConfig.LLM_BASE_URL}")
    print(f"    Temperature  → {ModelConfig.LLM_TEMPERATURE}")
    print(f"    Rate Limit   → ~{ModelConfig.OPENROUTER_RATE_LIMIT_RPM} req/min")
    print()
    print("  📐 Embedding Setup:")
    print(f"    Provider     → HuggingFace (FREE, local)")
    print(f"    Model        → {ModelConfig.EMBEDDING_MODEL}")
    print(f"    Dimensions   → {ModelConfig.EMBEDDING_DIMENSIONS}")
    print(f"    Device       → CPU (your Mac)")
    print()
    print("  🔑 API Keys:")
    for service, configured in keys.items():
        status = "✅ Configured" if configured else "❌ Missing"
        print(f"    {service:12s} → {status}")
    print()
    print("  💾 Storage:")
    print(f"    ChromaDB     → {StorageConfig.CHROMA_PERSIST_DIR}")
    print(f"    Checkpoints  → {StorageConfig.SQLITE_CHECKPOINT_PATH}")
    print(f"    Data Dir     → {StorageConfig.DATA_DIR}")
    print()
    print("  📚 RAG:")
    print(f"    Chunk Size   → {RAGConfig.CHUNK_SIZE}")
    print(f"    Search K     → {RAGConfig.SEARCH_K}")
    print(f"    Collection   → {RAGConfig.COLLECTION_NAME}")
    print()
    print("  💰 COST: $0.00 (everything is free!)")
    print("=" * 60)


# ──────────────────────────────────────────────
# Run on import: ensure directories exist
# ──────────────────────────────────────────────
StorageConfig.ensure_directories()
