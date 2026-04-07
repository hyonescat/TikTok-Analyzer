import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from api.server import app

client = TestClient(app)


def test_status_returns_idle():
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json()["status"] == "idle"


def test_results_returns_404_when_no_file(tmp_dir, monkeypatch):
    monkeypatch.chdir(tmp_dir)
    (tmp_dir / "output").mkdir()
    response = client.get("/api/results")
    assert response.status_code == 404


def test_run_returns_409_when_already_running():
    from api.server import _state
    _state["status"] = "running"
    response = client.post("/api/run", json={"favorites": 5, "liked": 5})
    assert response.status_code == 409
    _state["status"] = "idle"


def test_run_starts_when_idle():
    from api.server import _state
    _state["status"] = "idle"
    with patch("api.server._spawn_analyze", new_callable=AsyncMock):
        response = client.post("/api/run", json={"favorites": 5, "liked": 5})
    assert response.status_code == 200
    _state["status"] = "idle"
