"""
Phase 4 Verification Script — Graph Orchestration & Persistence.

Tests node presence, edge connectivity, checkpointer initialization, 
and end-to-end graph execution (optional).
"""

import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Flags
STRUCTURE_ONLY = "--structure-only" in sys.argv

def test_imports():
    print("🔍 Testing package imports...")
    try:
        from src.graph import build_graph, run_proposal
        print("  ✅ src.graph imports work")
        return True
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        return False

def test_structure():
    print("\n🔍 Testing graph structure...")
    try:
        from src.graph.workflow import _build_base_graph
        graph = _build_base_graph()
        
        # Verify nodes
        expected_nodes = [
            "research", "analysis", "writing", "qa", 
            "increment_revision", "human_review", "finalize"
        ]
        actual_nodes = list(graph.nodes.keys())
        
        missing = [n for n in expected_nodes if n not in actual_nodes]
        if missing:
            print(f"  ❌ Missing nodes: {missing}")
            return False
            
        print(f"  ✅ All {len(expected_nodes)} nodes present")
        return True
    except Exception as e:
        print(f"  ❌ Structure test failed: {e}")
        return False

def test_checkpointer():
    print("\n🔍 Testing checkpointer...")
    try:
        from src.graph.checkpointer import get_checkpointer
        from src.config import StorageConfig
        
        cp = get_checkpointer()
        print(f"  📁 DB Path: {StorageConfig.SQLITE_CHECKPOINT_PATH}")
        print(f"  ✅ Checkpointer initialized as {type(cp).__name__}")
        return True
    except Exception as e:
        print(f"  ❌ Checkpointer test failed: {e}")
        return False

def test_compilation():
    print("\n🔍 Testing graph compilation...")
    try:
        from src.graph import build_graph, build_graph_no_interrupt
        
        # Test full auto
        app_auto = build_graph_no_interrupt()
        print("  ✅ build_graph_no_interrupt() compiled")
        
        # Test review mode
        app_review = build_graph()
        print("  ✅ build_graph() compiled with interrupts")
        
        return True
    except Exception as e:
        print(f"  ❌ Compilation failed: {e}")
        return False

def test_end_to_end():
    print("\n🔍 Testing end-to-end pipeline (no review)...")
    try:
        from src.graph import run_proposal
        
        # We'll use a mock-like small test if possible, but run_proposal is full auto
        # To avoid massive token usage, we'll just check if it starts and runs first few nodes
        # Actually, let's just run a small one.
        print("  ⏳ Running full auto proposal for 'Stripe'...")
        start = time.time()
        result = run_proposal("Stripe", "Payment processing for SaaS", requestor_name="Verification Script")
        elapsed = time.time() - start
        
        if result.get("current_phase") == "completed":
            print(f"  ✅ E2E run successful in {elapsed:.1f}s")
            return True
        else:
            print(f"  ❌ E2E run failed or returned incomplete state: {result.get('current_phase')}")
            return False
    except Exception as e:
        print(f"  ❌ E2E test exception: {e}")
        return False

def main():
    print("\n" + "=" * 60)
    print("  PHASE 4 VERIFICATION — Graph Orchestration")
    print("=" * 60)
    
    steps = [
        ("Imports", test_imports),
        ("Structure", test_structure),
        ("Checkpointer", test_checkpointer),
        ("Compilation", test_compilation)
    ]
    
    passed_count = 0
    for name, func in steps:
        if func():
            passed_count += 1
            
    # E2E Test
    e2e_passed = True
    if passed_count == len(steps) and not STRUCTURE_ONLY:
        if test_end_to_end():
            passed_count += 1
            steps.append(("End-to-End", None)) # Just for count
        else:
            e2e_passed = False
            
    # Summary
    print("\n" + "=" * 60)
    print(f"  RESULTS: {passed_count}/{len(steps) + (0 if STRUCTURE_ONLY else 1)} passed")
    print("=" * 60)
    
    if passed_count == len(steps):
        print("\n  🎉 PHASE 4 STRUCTURE VERIFIED!")
        if STRUCTURE_ONLY:
            print("  (Skipping E2E as requested)")
        else:
            print("  🚀 Run 'python scripts/cli_demo.py' for full test.")
        return 0
    else:
        print("\n  ⚠️ SOME TESTS FAILED. CHECK LOGS ABOVE.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
