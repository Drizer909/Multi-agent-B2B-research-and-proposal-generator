"""
Phase 2 Verification Script — RAG Pipeline Edition

Tests:
1. Data file content (all files populated)
2. Ingestion pipeline (scans, chunks, embeds, stores)
3. Basic retrieval (similarity search)
4. Metadata filtering (industry, doc_type)
5. RAG Config integration

Usage:
    python scripts/verify_phase2.py
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def check_data_contents():
    print("\n🔍 Step 1: Checking data file contents...")
    from src.config import StorageConfig
    
    files_to_check = [
        StorageConfig.CASE_STUDIES_DIR / "saas_churn_reduction.md",
        StorageConfig.CASE_STUDIES_DIR / "fintech_onboarding.md",
        StorageConfig.CASE_STUDIES_DIR / "ecommerce_conversion.md",
        StorageConfig.CASE_STUDIES_DIR / "healthcare_compliance.md",
        StorageConfig.PRODUCT_DOCS_DIR / "platform_overview.md",
        StorageConfig.PRODUCT_DOCS_DIR / "pricing_tiers.md",
        StorageConfig.TEMPLATES_DIR / "proposal_template.md",
    ]
    
    all_good = True
    for f in files_to_check:
        if f.exists() and f.stat().st_size > 100:
            print(f"  ✅ {f.name} ({f.stat().st_size:,} bytes)")
        else:
            print(f"  ❌ {f.name} — MISSING or EMPTY!")
            all_good = False
    return all_good

def test_ingestion():
    print("\n🔍 Step 2: Testing ingestion pipeline...")
    try:
        from src.rag.ingest import ingest_documents
        start = time.time()
        count = ingest_documents()
        elapsed = time.time() - start
        
        if count > 0:
            print(f"\n  ✅ Ingested {count} chunks in {elapsed:.2f}s")
            return True
        else:
            print("  ❌ Ingestion returned 0 chunks")
            return False
    except Exception as e:
        print(f"  ❌ Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_retrieval():
    print("\n🔍 Step 3: Testing similarity retrieval...")
    try:
        from src.rag.retriever import get_retriever
        retriever = get_retriever()
        
        query = "SaaS churn reduction and predictive modeling"
        print(f"  ⏳ Querying: '{query}'...")
        
        docs = retriever.invoke(query)
        
        if len(docs) > 0:
            print(f"  ✅ Found {len(docs)} relevant documents")
            for i, doc in enumerate(docs[:2]):
                source = doc.metadata.get('filename', 'unknown')
                print(f"     {i+1}. [{source}] {doc.page_content[:80]}...")
            return True
        else:
            print("  ❌ No documents found for query")
            return False
    except Exception as e:
        print(f"  ❌ Retrieval failed: {e}")
        return False

def test_metadata_filtering():
    print("\n🔍 Step 4: Testing metadata filtering...")
    try:
        from src.rag.retriever import search_case_studies, search_product_docs
        
        # Test 1: Case studies only
        print("  ⏳ Filtering doc_type='case_study'...")
        cs_docs = search_case_studies("AI solutions")
        for doc in cs_docs:
            if doc.metadata.get('doc_type') != 'case_study':
                print(f"  ❌ Filter failed: Found {doc.metadata.get('doc_type')}")
                return False
        print(f"  ✅ Filtered to {len(cs_docs)} case studies")
        
        # Test 2: Industry filter
        industry = "Healthcare"
        print(f"  ⏳ Filtering industry='{industry}'...")
        h_docs = search_case_studies("compliance", industry=industry)
        for doc in h_docs:
            if industry.lower() not in doc.metadata.get('industry', '').lower():
                print(f"  ❌ Industry filter failed: Found {doc.metadata.get('industry')}")
                return False
        
        if len(h_docs) > 0:
            print(f"  ✅ Filtered to {len(h_docs)} {industry} documents")
        else:
             print(f"  ⚠️  No documents found for industry {industry} (check if ingestion worked)")
             return False
             
        return True
    except Exception as e:
        print(f"  ❌ Metadata filtering failed: {e}")
        return False

def main():
    print("=" * 70)
    print("  B2B PROPOSAL GENERATOR — Phase 2 Verification")
    print("  Stack: RAG Pipeline with ChromaDB + HuggingFace Local")
    print("=" * 70)

    results = {
        "Data Content": check_data_contents(),
        "Ingestion Pipeline": test_ingestion(),
        "Similarity Retrieval": test_retrieval(),
        "Metadata Filtering": test_metadata_filtering(),
    }

    print("\n" + "=" * 70)
    print("  VERIFICATION RESULTS")
    print("=" * 70)

    all_passed = True
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {check:35s} {status}")
        all_passed = all_passed and passed

    print("\n" + "=" * 70)
    if all_passed:
        print("  🚀 PHASE 2 VERIFIED! RAG Pipeline is solid.")
    else:
        print("  ⚠️  Fix the failures above.")
    print("=" * 70)

if __name__ == "__main__":
    main()
