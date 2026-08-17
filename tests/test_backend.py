"""Tests for the auslex-ui backend API."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

# Ensure the project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import backend.api
from backend.app import app
from backend.secrets import load_secrets, save_secrets, get_key, set_key


@pytest.fixture(autouse=True)
def _clear_secrets(tmp_path):
    """Use a temp secrets dir and out_root for every test."""
    secrets_dir = tmp_path / "secrets"
    runs_dir = tmp_path / "runs"
    questions_dir = tmp_path / "questions"
    
    # Create minimal question set
    questions_dir.mkdir(parents=True)
    (questions_dir / "auslex.jsonl").write_text(
        '[{"id":"q001","type":"mcq","priestley_area":"contract","jurisdiction":["Cth"],"difficulty":"pass","marks":10,"rubric":[{"criterion":"A","max":5},{"criterion":"B","max":5}],"canary":"x","version":"v1","question_text":"What is the law?","facts":null,"instructions":"Answer.","gold_answer":"A","required_authorities":[],"topics":[],"verification_hash":"abc","verification_note":""}]'
    )
    
    with patch("backend.secrets.SECRETS_DIR", secrets_dir):
        with patch("backend.secrets.SECRETS_FILE", secrets_dir / "keys.json"):
            with patch("backend.api.DEFAULT_OUT_ROOT", runs_dir):
                with patch("backend.api.DEFAULT_QUESTIONS", questions_dir / "auslex.jsonl"):
                    # Rebuild run_manager with new out_root
                    from backend.run_state import RunManager
                    from backend.api import run_manager as _orig_rm
                    backend.api.run_manager = RunManager(out_root=runs_dir)
                    yield
                    # Restore original
                    backend.api.run_manager = _orig_rm


@pytest.fixture
def client():
    return TestClient(app)


class TestHealth:
    def test_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"


class TestSlots:
    def test_slots(self, client):
        r = client.get("/api/slots")
        assert r.status_code == 200
        slots = r.json()
        assert len(slots) == 4
        names = [s["name"] for s in slots]
        assert "gpt" in names
        assert "claude" in names
        assert "gemini" in names
        assert "local" in names


class TestQuestions:
    def test_questions_list(self, client):
        r = client.get("/api/questions")
        assert r.status_code == 200
        questions = r.json()
        assert isinstance(questions, list)
        assert len(questions) > 0

    def test_question_detail(self, client):
        r = client.get("/api/questions/q001")
        assert r.status_code == 200
        q = r.json()
        assert q["id"] == "q001"
        assert "question_text" in q


class TestKeys:
    def test_get_keys_no_keys(self, client):
        r = client.get("/api/keys")
        assert r.status_code == 200
        data = r.json()
        assert data["openai_key"] is None
        assert data["anthropic_key"] is None
        assert data["google_key"] is None
        assert data["local_base_url"] == "http://localhost:10000/v1"
        assert data["local_model"] == "14. Qwen3.8-27B (Q5_K_M)"
        assert data["local_enable_thinking"] is False

    def test_set_keys(self, client, tmp_path):
        r = client.put(
            "/api/keys",
            json={
                "openai_key": "sk-test-123",
                "anthropic_key": "ant-test-123",
                "local_base_url": "http://localhost:9000/v1",
                "local_model": "my-model",
                "local_enable_thinking": True,
            },
        )
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

        # Verify they were persisted
        with patch("backend.secrets.SECRETS_DIR", tmp_path / "secrets"):
            data = load_secrets()
            assert data["openai_key"] == "sk-test-123"
            assert data["anthropic_key"] == "ant-test-123"

    def test_test_connection_unknown_provider(self, client):
        r = client.post("/api/keys/test/unknown")
        assert r.status_code == 422


class TestRuns:
    def test_list_runs_empty(self, client):
        r = client.get("/api/runs")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_run(self, client, tmp_path):
        r = client.post(
            "/api/runs",
            json={
                "models": ["gpt", "local"],
                "n_reps": 2,
                "base_seed": 42,
            },
        )
        assert r.status_code == 201
        data = r.json()
        assert "run_id" in data
        run_id = data["run_id"]

        r2 = client.get("/api/runs")
        runs = r2.json()
        assert len(runs) == 1
        assert runs[0]["run_id"] == run_id
        assert runs[0]["models"] == ["gpt", "local"]
        assert runs[0]["n_reps"] == 2

    def test_run_status(self, client, tmp_path):
        r = client.post("/api/runs", json={"models": ["gpt"], "n_reps": 1, "base_seed": 0})
        run_id = r.json()["run_id"]

        r2 = client.get(f"/api/runs/{run_id}/status")
        assert r2.status_code == 200
        status = r2.json()
        assert status["run_id"] == run_id
        assert status["status"] in ("pending", "running", "done", "error")

    def test_run_not_found(self, client):
        r = client.get("/api/runs/nonexistent/status")
        assert r.status_code == 404

    def test_item_results_not_found(self, client):
        r = client.get("/api/runs/nonexistent/item-results?model=gpt&question=q001")
        assert r.status_code == 404


class TestLocalProbe:
    def test_probe_local(self, client):
        r = client.get("/api/local/probe")
        assert r.status_code == 200
        data = r.json()
        assert "reachable" in data
        assert "models" in data


class TestExport:
    def test_export_site_not_found(self, client):
        r = client.post("/api/runs/nonexistent/export-site")
        assert r.status_code == 404

    def test_export_hf_not_found(self, client):
        r = client.post("/api/runs/nonexistent/export-hf")
        assert r.status_code == 404


class TestSecretsFunctions:
    def test_default_values(self, tmp_path):
        with patch("backend.secrets.SECRETS_DIR", tmp_path / "secrets"):
            data = load_secrets()
            assert data == {}

    def test_set_and_get(self, tmp_path):
        with patch("backend.secrets.SECRETS_DIR", tmp_path / "secrets"):
            set_key("openai", "sk-1")
            set_key("anthropic", "ant-1")
            assert get_key("openai") == "sk-1"
            assert get_key("anthropic") == "ant-1"
            assert get_key("google") is None

    def test_file_permissions(self, tmp_path):
        with patch("backend.secrets.SECRETS_DIR", tmp_path / "secrets"):
            set_key("openai", "sk-1")
            secrets_file = tmp_path / "secrets" / "keys.json"
            mode = secrets_file.stat().st_mode
            assert mode & 0o777 == 0o600


class TestCLI:
    def test_cli_main(self):
        """Test that the CLI entrypoint can be imported."""
        from backend.cli import main
        assert callable(main)
