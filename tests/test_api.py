"""
Unit tests for API routes and thread ID state persistence.
"""

from fastapi.testclient import TestClient
from src.api.app import app
from src.api.routes import _jobs

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "api_keys" in data
    assert "components" in data

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data

def test_proposal_status_not_found():
    response = client.get("/proposal/status/async_non_existent_thread_99999")
    assert response.status_code == 404

def test_proposal_status_in_memory():
    thread_id = "async_test_company_12345"
    _jobs[thread_id] = {
        "status": "running",
        "company_name": "Test Company",
        "current_phase": "research",
        "error": "",
        "started_at": ""
    }
    
    response = client.get(f"/proposal/status/{thread_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["thread_id"] == thread_id
    assert data["status"] == "running"
    assert data["company_name"] == "Test Company"
    assert data["current_phase"] == "research"


def test_async_job_reports_active_agent_before_completion(monkeypatch, tmp_path):
    from threading import Event

    from src.config import StorageConfig
    from src.graph import workflow

    entered_analysis = Event()
    release_analysis = Event()

    def analyze(state):
        entered_analysis.set()
        assert release_analysis.wait(timeout=10)
        return {"current_phase": "analysis_complete"}

    monkeypatch.setattr(StorageConfig, "SQLITE_CHECKPOINT_PATH", str(tmp_path / "jobs.db"))
    monkeypatch.setattr(workflow, "research_agent", lambda state: {"current_phase": "research_complete"})
    monkeypatch.setattr(workflow, "analysis_agent", analyze)
    monkeypatch.setattr(workflow, "writing_agent", lambda state: {"proposal_draft": "# Test proposal"})
    monkeypatch.setattr(workflow, "qa_agent", lambda state: {"qa_score": 1.0})

    with TestClient(app) as live_client:
        response = live_client.post("/proposal/generate/async", json={
            "company_name": "Progress Test",
            "user_request": "Generate a test proposal.",
        })
        assert response.status_code == 200
        thread_id = response.json()["thread_id"]
        try:
            assert entered_analysis.wait(timeout=5)
            response = live_client.get(f"/proposal/status/{thread_id}")
            assert response.headers["cache-control"] == "no-store"
            assert response.json()["status"] == "running"
            assert response.json()["current_phase"] == "analysis"
            assert live_client.get(f"/proposal/result/{thread_id}").status_code == 202
        finally:
            release_analysis.set()

    assert _jobs.pop(thread_id)["status"] == "completed"
    response = client.get(f"/proposal/result/{thread_id}")
    assert response.status_code == 200
    assert response.json()["final_proposal"] == "# Test proposal"
