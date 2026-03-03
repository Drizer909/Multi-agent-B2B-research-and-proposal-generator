"""
Phase 5 Verification — API Layer & PDF Export.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_imports():
    print("\n🔍 Test 1: Checking imports...")
    try:
        from src.api.models import ProposalRequest
        from src.api.pdf_export import export_to_pdf
        from src.api.routes import router
        from src.api.app import app
        print("  ✅ All imports successful")
        return True
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        return False

def test_health_endpoint():
    print("\n🔍 Test 2: Testing GET /health endpoint...")
    try:
        from fastapi.testclient import TestClient
        from src.api.app import app
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        print(f"  ✅ Health: {response.json()['status']}")
        return True
    except Exception as e:
        print(f"  ❌ Health endpoint failed: {e}")
        return False

def test_markdown_export():
    print("\n🔍 Test 3: Testing Markdown export...")
    try:
        from fastapi.testclient import TestClient
        from src.api.app import app
        client = TestClient(app)
        response = client.post(
            "/proposal/export/markdown",
            json={
                "proposal_markdown": "# Test Proposal",
                "company_name": "TestCo",
            },
        )
        assert response.status_code == 200
        print(f"  ✅ Markdown export: {len(response.content)} bytes")
        return True
    except Exception as e:
        print(f"  ❌ Markdown export failed: {e}")
        return False

def main():
    print("\n" + "═" * 60)
    print("  PHASE 5 VERIFICATION — API Layer")
    print("═" * 60)
    
    results = [test_imports(), test_health_endpoint(), test_markdown_export()]
    
    if all(results):
        print("\n  🎉 Phase 5 COMPLETE! API layer is ready.")
        return 0
    else:
        print("\n  ⚠️ Some tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
