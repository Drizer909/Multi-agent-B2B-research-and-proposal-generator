"""
Phase 1 Verification Script — OpenRouter + Llama 3.3 70B Edition

Usage:
    python scripts/verify_phase1.py
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_project_structure():
    """Verify all required directories and files exist."""
    print("\n🔍 Step 1: Checking project structure...")

    required = [
        "src/__init__.py",
        "src/config.py",
        "src/state/__init__.py",
        "src/state/schema.py",
        "src/agents/__init__.py",
        "src/tools/__init__.py",
        "src/rag/__init__.py",
        "src/graph/__init__.py",
        "src/api/__init__.py",
        "requirements.txt",
        ".env",
        ".gitignore",
    ]

    all_good = True
    for path in required:
        full_path = PROJECT_ROOT / path
        if full_path.exists():
            print(f"  ✅ {path}")
        else:
            print(f"  ❌ {path} — MISSING!")
            all_good = False

    return all_good


def check_imports():
    """Verify all required packages are installed."""
    print("\n🔍 Step 2: Checking package imports...")

    packages = {
        "langgraph": "langgraph",
        "langchain": "langchain",
        "langchain_openai": "langchain-openai",
        "langchain_community": "langchain-community",
        "langchain_huggingface": "langchain-huggingface",
        "sentence_transformers": "sentence-transformers",
        "chromadb": "chromadb",
        "tavily": "tavily-python",
        "fastapi": "fastapi",
        "pydantic": "pydantic",
        "dotenv": "python-dotenv",
        "langchain_text_splitters": "langchain-text-splitters",
    }

    all_good = True
    for module, pip_name in packages.items():
        try:
            __import__(module)
            print(f"  ✅ {pip_name}")
        except ImportError:
            print(f"  ❌ {pip_name} — run: pip install {pip_name}")
            all_good = False

    return all_good


def check_config():
    """Verify configuration loads correctly."""
    print("\n🔍 Step 3: Checking configuration...")
    try:
        from src.config import print_config_status

        print_config_status()
        return True
    except Exception as e:
        print(f"  ❌ Config error: {e}")
        return False


def check_state_schema():
    """Verify state schema works."""
    print("\n🔍 Step 4: Checking state schema...")
    try:
        from src.state.schema import (
            ProposalState,
            create_initial_state,
            print_state_summary,
        )

        state = create_initial_state(
            company_name="Test Corp",
            user_request="Test proposal for verification",
        )

        assert state["company_name"] == "Test Corp"
        assert state["pain_points"] == []
        assert state["revision_count"] == 0
        assert state["approved"] is False
        assert state["messages"] == []

        print_state_summary(state)

        state["pain_points"] = state["pain_points"] + ["test pain point"]
        assert len(state["pain_points"]) == 1

        print("  ✅ State schema is valid")
        print("  ✅ Initial state factory works")
        print("  ✅ State summary printer works")
        return True
    except Exception as e:
        print(f"  ❌ State schema error: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_data_files():
    """Verify all sample data files exist."""
    print("\n🔍 Step 5: Checking data files...")
    from src.config import StorageConfig

    expected_files = {
        "case_studies": [
            "saas_churn_reduction.md",
            "fintech_onboarding.md",
            "ecommerce_conversion.md",
            "healthcare_compliance.md",
            "saas_lead_scoring.md",
        ],
        "product_docs": [
            "platform_overview.md",
            "pricing_tiers.md",
        ],
        "templates": [
            "proposal_template.md",
        ],
    }

    all_good = True
    for folder, files in expected_files.items():
        folder_path = StorageConfig.DATA_DIR / folder
        for filename in files:
            file_path = folder_path / filename
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"  ✅ {folder}/{filename} ({size:,} bytes)")
            else:
                print(f"  ❌ {folder}/{filename} — MISSING!")
                all_good = False

    return all_good


def check_llm_connection():
    """Test the OpenRouter / Llama 3.3 connection."""
    print("\n🔍 Step 6: Testing Llama 3.3 70B via OpenRouter...")
    from src.config import APIKeys

    keys = APIKeys.validate()
    if not keys["openrouter"]:
        print("  ⚠️  OPENROUTER_API_KEY not set — skipping LLM test")
        print("  ℹ️  Get your FREE key at https://openrouter.ai/settings/keys")
        return True  # Don't fail, just warn

    try:
        from src.config import ModelConfig

        print(f"  ⏳ Connecting to OpenRouter ({ModelConfig.LLM_MODEL})...")
        llm = ModelConfig.get_llm()

        start = time.time()
        response = llm.invoke("Say exactly: 'Hello from Llama 3.3 via OpenRouter!'")
        elapsed = time.time() - start

        print(f"  ✅ LLM responded in {elapsed:.2f}s")
        print(f"  📝 Response: {response.content[:150]}")
        print(f"  🏷️  Model: {ModelConfig.LLM_MODEL}")
        print(f"  🌐 Provider: OpenRouter ({ModelConfig.LLM_BASE_URL})")
        print(f"  💰 Cost: $0.00 (FREE model)")

        # Check response metadata if available
        if hasattr(response, "response_metadata") and response.response_metadata:
            meta = response.response_metadata
            if "model_name" in meta:
                print(f"  📌 Actual model used: {meta['model_name']}")
            if "token_usage" in meta:
                usage = meta["token_usage"]
                print(
                    f"  📊 Tokens: {usage.get('prompt_tokens', '?')} in, "
                    f"{usage.get('completion_tokens', '?')} out"
                )

        return True
    except Exception as e:
        error_str = str(e)
        print(f"  ❌ LLM connection failed: {error_str[:200]}")

        if "401" in error_str or "auth" in error_str.lower():
            print("  💡 Fix: Check your OPENROUTER_API_KEY in .env")
        elif "429" in error_str or "rate" in error_str.lower():
            print("  💡 Fix: Rate limited. Wait a minute and try again.")
        elif "model" in error_str.lower():
            print("  💡 Fix: Model ID might have changed. Check https://openrouter.ai/models")

        return False


def check_embeddings():
    """Test that HuggingFace embeddings work locally."""
    print("\n🔍 Step 7: Testing HuggingFace Embeddings (local)...")
    try:
        from src.config import ModelConfig

        print("  ⏳ Loading embedding model (first time downloads ~90MB)...")
        start = time.time()
        embeddings = ModelConfig.get_embeddings()
        load_time = time.time() - start
        print(f"  ✅ Model loaded in {load_time:.2f}s")

        start = time.time()
        test_texts = [
            "Customer churn reduction for SaaS companies",
            "Healthcare compliance automation",
        ]
        vectors = embeddings.embed_documents(test_texts)
        embed_time = time.time() - start

        print(f"  ✅ Embedded {len(test_texts)} documents in {embed_time:.3f}s")
        print(f"  📐 Vector dimensions: {len(vectors[0])}")
        print(f"  🏷️  Model: {ModelConfig.EMBEDDING_MODEL}")
        print(f"  💰 Cost: $0.00 (runs locally on your Mac)")

        assert len(vectors[0]) == ModelConfig.EMBEDDING_DIMENSIONS, (
            f"Expected {ModelConfig.EMBEDDING_DIMENSIONS} dims, got {len(vectors[0])}"
        )
        print(f"  ✅ Dimensions match config ({ModelConfig.EMBEDDING_DIMENSIONS})")

        return True
    except Exception as e:
        print(f"  ❌ Embedding error: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("  B2B PROPOSAL GENERATOR — Phase 1 Verification")
    print("  Stack: Llama 3.3 70B (OpenRouter) + HuggingFace Local")
    print("=" * 60)

    results = {
        "Project Structure": check_project_structure(),
        "Package Imports": check_imports(),
        "Configuration": check_config(),
        "State Schema": check_state_schema(),
        "Data Files": check_data_files(),
        "LLM (OpenRouter/Llama 3.3)": check_llm_connection(),
        "Embeddings (HuggingFace)": check_embeddings(),
    }

    print("\n")
    print("=" * 60)
    print("  VERIFICATION RESULTS")
    print("=" * 60)
    all_passed = True
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {check:30s} {status}")
        if not passed:
            all_passed = False

    print()
    print(f"  💰 Total cost of this entire stack: $0.00")
    print()
    if all_passed:
        print("  🎉 Phase 1 COMPLETE! Ready for Phase 2 (RAG Pipeline)")
    else:
        print("  ⚠️  Fix the issues above before proceeding.")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
