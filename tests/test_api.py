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
        "result": {"current_phase": "research"},
        "error": "",
        "started_at": 1000.0
    }
    
    response = client.get(f"/proposal/status/{thread_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["thread_id"] == thread_id
    assert data["status"] == "running"
    assert data["company_name"] == "Test Company"
    assert data["current_phase"] == "research"
