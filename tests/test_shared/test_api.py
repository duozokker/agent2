"""Tests for shared.api module -- FastAPI app factory."""

from __future__ import annotations

import os
import types
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from pydantic_ai import ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.exceptions import ModelAPIError

from shared.message_history import serialize_messages


@pytest.fixture(autouse=True)
def _disable_learnings_in_tests():
    """Prevent learnings injection from polluting test assertions."""
    os.environ["AGENT2_DISABLE_LEARNINGS"] = "1"
    yield
    os.environ.pop("AGENT2_DISABLE_LEARNINGS", None)


@pytest.fixture
def app():
    """Create a test app instance."""
    os.environ["AGENT_NAME"] = "example-agent"
    from shared.api import create_app

    return create_app("example-agent")


def test_health_endpoint(app):
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["agent"] == "example-agent"


def test_tasks_requires_auth_problem_json(app):
    with TestClient(app) as client:
        resp = client.post("/tasks", json={"input": {"text": "hello"}})
        assert resp.status_code == 401
        assert resp.headers["content-type"].startswith("application/problem+json")
        assert resp.json()["title"] == "Unauthorized"


def test_tasks_invalid_json(app, auth_headers):
    with TestClient(app) as client:
        resp = client.post(
            "/tasks?mode=sync",
            content="not valid json{{{",
            headers={**auth_headers, "Content-Type": "application/json"},
        )
        assert resp.status_code == 400


def test_tasks_json_array_body(app, auth_headers):
    with TestClient(app) as client:
        resp = client.post("/tasks?mode=sync", json=[1, 2, 3], headers=auth_headers)
        assert resp.status_code == 422


def test_tasks_input_must_be_object(app, auth_headers):
    with TestClient(app) as client:
        resp = client.post("/tasks?mode=sync", json={"input": [1, 2, 3]}, headers=auth_headers)
        assert resp.status_code == 422
        assert "input" in resp.json()["detail"].lower()


def test_tasks_sync_mock_mode_uses_real_source_import(app, auth_headers, monkeypatch):
    """Source-layout imports should work without monkeypatching agent modules."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "")

    with TestClient(app) as client:
        resp = client.post(
            "/tasks?mode=sync",
            json={"input": {"text": "hello world"}},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] == "completed"
        assert payload["result"]["title"]


def test_tasks_async_mode(app, auth_headers, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    with TestClient(app) as client:
        resp = client.post("/tasks?mode=async", json={"input": {"text": "hello world"}}, headers=auth_headers)
        assert resp.status_code == 202
        assert "task_id" in resp.json()


def test_tasks_sync_mock_mode_calls_after_run(auth_headers, monkeypatch):
    """Mock mode still executes after_run so hosts can persist conversation state."""
    from shared.api import create_app

    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    message_history = serialize_messages(
        [
            ModelRequest(parts=[UserPromptPart(content="Hello")]),
            ModelResponse(parts=[TextPart(content="Hi")]),
        ]
    )

    fake_module = types.ModuleType("agent.agent")
    fake_module.agent = MagicMock()  # type: ignore[attr-defined]
    fake_module.after_run = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    monkeypatch.setattr("importlib.import_module", lambda _path: fake_module)

    app = create_app("example-agent")
    with TestClient(app) as client:
        resp = client.post(
            "/tasks?mode=sync",
            json={"input": {"text": "hello world", "message_history": message_history}},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    fake_module.after_run.assert_awaited_once()
    hook_input, output = fake_module.after_run.await_args.args
    assert hook_input == {"text": "hello world", "message_history": message_history}
    assert output["_message_history"] == message_history


def test_tasks_sync_provider_auth_fallback_calls_after_run(auth_headers, monkeypatch):
    """Provider auth fallback should return a mocked result and persist it."""
    from shared.api import create_app

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    message_history = serialize_messages(
        [
            ModelRequest(parts=[UserPromptPart(content="Hello")]),
            ModelResponse(parts=[TextPart(content="Hi")]),
        ]
    )

    class FakeAgent:
        async def run(self, *_args, **_kwargs):
            raise ModelAPIError("openrouter:anthropic/claude-sonnet-4", "status_code: 401 unauthorized")

    fake_module = types.ModuleType("agent.agent")
    fake_module.agent = FakeAgent()  # type: ignore[attr-defined]
    fake_module.after_run = AsyncMock(return_value=None)  # type: ignore[attr-defined]
    monkeypatch.setattr("importlib.import_module", lambda _path: fake_module)

    app = create_app("example-agent")
    with TestClient(app) as client:
        resp = client.post(
            "/tasks?mode=sync",
            json={"input": {"text": "hello world", "message_history": message_history}},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["result"]["_mock_reason"] == "provider_auth_failed"

    fake_module.after_run.assert_awaited_once()


def test_tasks_sync_generic_provider_auth_error_falls_back(auth_headers, monkeypatch):
    from shared.api import create_app

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")

    class FakeAgent:
        async def run(self, *_args, **_kwargs):
            raise RuntimeError("status_code: 401, body: {'message': 'User not found.', 'code': 401}")

    fake_module = types.ModuleType("agent.agent")
    fake_module.agent = FakeAgent()  # type: ignore[attr-defined]
    monkeypatch.setattr("importlib.import_module", lambda _path: fake_module)

    app = create_app("example-agent")
    with TestClient(app) as client:
        resp = client.post(
            "/tasks?mode=sync",
            json={"input": {"text": "hello world"}},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    assert resp.json()["result"]["_mock_reason"] == "provider_auth_failed"


def test_tasks_sync_passes_raw_message_history_into_before_run(auth_headers, monkeypatch):
    from shared.api import create_app

    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    message_history = serialize_messages([ModelRequest(parts=[UserPromptPart(content="resume me")])])

    fake_module = types.ModuleType("agent.agent")
    fake_module.agent = MagicMock()  # type: ignore[attr-defined]
    fake_module.before_run = MagicMock(return_value={"text": "hello world"})  # type: ignore[attr-defined]
    monkeypatch.setattr("importlib.import_module", lambda _path: fake_module)

    app = create_app("example-agent")
    with TestClient(app) as client:
        resp = client.post(
            "/tasks?mode=sync",
            json={"input": {"text": "hello world", "message_history": message_history}},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    fake_module.before_run.assert_called_once_with({"text": "hello world", "message_history": message_history})


def test_tasks_sync_surfaces_before_run_failures_as_problem(auth_headers, monkeypatch):
    from shared.api import create_app

    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    fake_module = types.ModuleType("agent.agent")
    fake_module.agent = MagicMock()  # type: ignore[attr-defined]
    fake_module.before_run = MagicMock(side_effect=ValueError("OCR tool missing"))  # type: ignore[attr-defined]
    monkeypatch.setattr("importlib.import_module", lambda _path: fake_module)

    app = create_app("example-agent")
    with TestClient(app) as client:
        resp = client.post(
            "/tasks?mode=sync",
            json={"input": {"text": "hello world"}},
            headers=auth_headers,
        )
        assert resp.status_code == 500
        assert resp.headers["content-type"].startswith("application/problem+json")
        assert resp.json()["title"] == "Agent Precondition Failed"


def test_tasks_sync_passes_before_run_toolsets_to_agent_run(auth_headers, monkeypatch):
    """before_run may provide fresh per-run MCP toolsets without leaking them into the prompt."""
    from shared.api import create_app

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    toolsets = [object()]
    captured: dict[str, object] = {}

    class FakeOutput:
        def model_dump(self, mode: str = "json") -> dict[str, object]:
            return {"status": "complete"}

    class FakeRunResult:
        output = FakeOutput()

        def all_messages(self) -> list:
            return []

    class FakeAgent:
        async def run(self, input_str: str, **kwargs):
            captured["input_str"] = input_str
            captured["kwargs"] = kwargs
            return FakeRunResult()

    fake_module = types.ModuleType("agent.agent")
    fake_module.agent = FakeAgent()  # type: ignore[attr-defined]
    fake_module.before_run = MagicMock(  # type: ignore[attr-defined]
        return_value={
            "text": "hello world",
            "_instructions": "Dynamic instructions",
            "_toolsets": toolsets,
        }
    )
    monkeypatch.setattr("importlib.import_module", lambda _path: fake_module)

    app = create_app("example-agent")
    with TestClient(app) as client:
        resp = client.post(
            "/tasks?mode=sync",
            json={"input": {"text": "hello world"}},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    assert captured["input_str"] == '{"text": "hello world"}'
    assert captured["kwargs"]["instructions"] == "Dynamic instructions"  # type: ignore[index]
    assert captured["kwargs"]["toolsets"] is toolsets  # type: ignore[index]


def test_execute_pending_action_endpoint(auth_headers, monkeypatch):
    from shared.api import create_app

    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    approval_app = create_app("approval-demo")
    with TestClient(approval_app) as client:
        create_resp = client.post(
            "/tasks?mode=async",
            json={
                "input": {
                    "text": "Create an approval task",
                    "require_approval": True,
                }
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 202
        task_id = create_resp.json()["task_id"]

        for _ in range(20):
            task_resp = client.get(f"/tasks/{task_id}", headers=auth_headers)
            if task_resp.json()["status"] == "completed":
                break
        else:
            pytest.fail("Approval demo task did not complete in time")

        action_resp = client.post(
            f"/tasks/{task_id}/actions/execute",
            json={"action": "store_note"},
            headers=auth_headers,
        )
        assert action_resp.status_code == 200
        assert action_resp.json()["success"] is True

        task_resp = client.get(f"/tasks/{task_id}", headers=auth_headers)
        assert task_resp.status_code == 200
        assert task_resp.json()["result"]["pending_actions"] == []
