"""Unit tests for all 15 Hamlet hook scripts in hooks/."""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

HOOKS_DIR = os.path.join(os.path.dirname(__file__), "..", "hooks")

SERVER_URL = "http://localhost:8080/hamlet/event"
PROJECT_ID = "test-project-id"
PROJECT_NAME = "Test Project"

BASE_PAYLOAD = {"session_id": "test-session", "cwd": "/tmp"}


def load_hook(name: str):
    """Load a hook module fresh from its file path."""
    path = os.path.join(HOOKS_DIR, f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_urlopen_mock():
    """Return a MagicMock suitable for patching urllib.request.urlopen."""
    mock = MagicMock()
    mock.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock.return_value.__exit__ = MagicMock(return_value=False)
    return mock


# ---------------------------------------------------------------------------
# Tests for each hook
# ---------------------------------------------------------------------------


class TestPreToolUse:
    def test_pre_tool_use(self, monkeypatch, tmp_path):
        payload = {
            **BASE_PAYLOAD,
            "tool_name": "Read",
            "tool_input": {"path": "/tmp/x"},
        }
        module = load_hook("pre_tool_use")

        # Patch Path.home() so the timing dir goes to tmp_path
        monkeypatch.setattr(module, "TIMING_DIR", tmp_path / "timing")

        mock_urlopen = make_urlopen_mock()
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        monkeypatch.setattr(module, "find_server_url", lambda: SERVER_URL)
        monkeypatch.setattr(module, "find_config", lambda: (PROJECT_ID, PROJECT_NAME))
        monkeypatch.setattr(module.urllib.request, "urlopen", mock_urlopen)

        with pytest.raises(SystemExit) as exc_info:
            module.main()

        assert exc_info.value.code == 0
        assert mock_urlopen.called

        captured_request = mock_urlopen.call_args[0][0]
        body = json.loads(captured_request.data.decode())
        assert body["method"] == "hamlet/event"
        assert body["params"]["hook_type"] == "PreToolUse"


class TestPostToolUse:
    def test_post_tool_use(self, monkeypatch, tmp_path):
        payload = {
            **BASE_PAYLOAD,
            "tool_name": "Write",
            "success": True,
        }
        module = load_hook("post_tool_use")

        # Patch TIMING_DIR to tmp_path to avoid writing real files
        monkeypatch.setattr(module, "TIMING_DIR", tmp_path / "timing")

        mock_urlopen = make_urlopen_mock()
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        monkeypatch.setattr(module, "find_server_url", lambda: SERVER_URL)
        monkeypatch.setattr(module, "find_config", lambda: (PROJECT_ID, PROJECT_NAME))
        monkeypatch.setattr(module.urllib.request, "urlopen", mock_urlopen)

        with pytest.raises(SystemExit) as exc_info:
            module.main()

        assert exc_info.value.code == 0
        assert mock_urlopen.called

        captured_request = mock_urlopen.call_args[0][0]
        body = json.loads(captured_request.data.decode())
        assert body["method"] == "hamlet/event"
        assert body["params"]["hook_type"] == "PostToolUse"


class TestNotification:
    def test_notification(self, monkeypatch):
        payload = {**BASE_PAYLOAD, "data": {"message": "test notification"}}
        module = load_hook("notification")

        mock_urlopen = make_urlopen_mock()
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        monkeypatch.setattr(module, "find_server_url", lambda: SERVER_URL)
        monkeypatch.setattr(module, "find_config", lambda: (PROJECT_ID, PROJECT_NAME))
        monkeypatch.setattr(module.urllib.request, "urlopen", mock_urlopen)

        with pytest.raises(SystemExit) as exc_info:
            module.main()

        assert exc_info.value.code == 0
        assert mock_urlopen.called

        captured_request = mock_urlopen.call_args[0][0]
        body = json.loads(captured_request.data.decode())
        assert body["method"] == "hamlet/event"
        assert body["params"]["hook_type"] == "Notification"


class TestStop:
    def test_stop(self, monkeypatch):
        payload = {**BASE_PAYLOAD, "data": {"reason": "stop"}}
        module = load_hook("stop")

        mock_urlopen = make_urlopen_mock()
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        monkeypatch.setattr(module, "find_server_url", lambda: SERVER_URL)
        monkeypatch.setattr(module, "find_config", lambda: (PROJECT_ID, PROJECT_NAME))
        monkeypatch.setattr(module.urllib.request, "urlopen", mock_urlopen)

        with pytest.raises(SystemExit) as exc_info:
            module.main()

        assert exc_info.value.code == 0
        assert mock_urlopen.called

        captured_request = mock_urlopen.call_args[0][0]
        body = json.loads(captured_request.data.decode())
        assert body["method"] == "hamlet/event"
        assert body["params"]["hook_type"] == "Stop"


class TestSessionStart:
    def test_session_start(self, monkeypatch):
        payload = {**BASE_PAYLOAD, "source": "test"}
        module = load_hook("session_start")

        mock_urlopen = make_urlopen_mock()
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        monkeypatch.setattr(module, "find_server_url", lambda: SERVER_URL)
        monkeypatch.setattr(module, "find_config", lambda: (PROJECT_ID, PROJECT_NAME))
        monkeypatch.setattr(module.os, "chdir", lambda path: None)
        monkeypatch.setattr(module.os.path, "isdir", lambda path: True)
        monkeypatch.setattr(module.urllib.request, "urlopen", mock_urlopen)

        with pytest.raises(SystemExit) as exc_info:
            module.main()

        assert exc_info.value.code == 0
        assert mock_urlopen.called

        captured_request = mock_urlopen.call_args[0][0]
        body = json.loads(captured_request.data.decode())
        assert body["method"] == "hamlet/event"
        assert body["params"]["hook_type"] == "SessionStart"


class TestSessionEnd:
    def test_session_end(self, monkeypatch):
        payload = {**BASE_PAYLOAD, "reason": "end"}
        module = load_hook("session_end")

        mock_urlopen = make_urlopen_mock()
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        monkeypatch.setattr(module, "find_server_url", lambda: SERVER_URL)
        monkeypatch.setattr(module, "find_config", lambda: (PROJECT_ID, PROJECT_NAME))
        monkeypatch.setattr(module.os, "chdir", lambda path: None)
        monkeypatch.setattr(module.os.path, "isdir", lambda path: True)
        monkeypatch.setattr(module.urllib.request, "urlopen", mock_urlopen)

        with pytest.raises(SystemExit) as exc_info:
            module.main()

        assert exc_info.value.code == 0
        assert mock_urlopen.called

        captured_request = mock_urlopen.call_args[0][0]
        body = json.loads(captured_request.data.decode())
        assert body["method"] == "hamlet/event"
        assert body["params"]["hook_type"] == "SessionEnd"


class TestSubagentStart:
    def test_subagent_start(self, monkeypatch):
        payload = {**BASE_PAYLOAD, "agent_id": "a1", "agent_type": "coder"}
        module = load_hook("subagent_start")

        mock_urlopen = make_urlopen_mock()
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        monkeypatch.setattr(module, "find_server_url", lambda: SERVER_URL)
        monkeypatch.setattr(module, "find_config", lambda: (PROJECT_ID, PROJECT_NAME))
        monkeypatch.setattr(module.os, "chdir", lambda path: None)
        monkeypatch.setattr(module.os.path, "isdir", lambda path: True)
        monkeypatch.setattr(module.urllib.request, "urlopen", mock_urlopen)

        with pytest.raises(SystemExit) as exc_info:
            module.main()

        assert exc_info.value.code == 0
        assert mock_urlopen.called

        captured_request = mock_urlopen.call_args[0][0]
        body = json.loads(captured_request.data.decode())
        assert body["method"] == "hamlet/event"
        assert body["params"]["hook_type"] == "SubagentStart"


class TestSubagentStop:
    def test_subagent_stop(self, monkeypatch):
        payload = {**BASE_PAYLOAD, "agent_id": "a1", "agent_type": "coder"}
        module = load_hook("subagent_stop")

        mock_urlopen = make_urlopen_mock()
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        monkeypatch.setattr(module, "find_server_url", lambda: SERVER_URL)
        monkeypatch.setattr(module, "find_config", lambda: (PROJECT_ID, PROJECT_NAME))
        monkeypatch.setattr(module.os, "chdir", lambda path: None)
        monkeypatch.setattr(module.os.path, "isdir", lambda path: True)
        monkeypatch.setattr(module.urllib.request, "urlopen", mock_urlopen)

        with pytest.raises(SystemExit) as exc_info:
            module.main()

        assert exc_info.value.code == 0
        assert mock_urlopen.called

        captured_request = mock_urlopen.call_args[0][0]
        body = json.loads(captured_request.data.decode())
        assert body["method"] == "hamlet/event"
        assert body["params"]["hook_type"] == "SubagentStop"


class TestTeammateIdle:
    def test_teammate_idle(self, monkeypatch):
        payload = {
            **BASE_PAYLOAD,
            "task_id": "t1",
            "task_subject": "test",
            "teammate_name": "alice",
        }
        module = load_hook("teammate_idle")

        mock_urlopen = make_urlopen_mock()
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        monkeypatch.setattr(module, "find_server_url", lambda: SERVER_URL)
        monkeypatch.setattr(module, "find_config", lambda: (PROJECT_ID, PROJECT_NAME))
        monkeypatch.setattr(module.os, "chdir", lambda path: None)
        monkeypatch.setattr(module.os.path, "isdir", lambda path: True)
        monkeypatch.setattr(module.urllib.request, "urlopen", mock_urlopen)

        with pytest.raises(SystemExit) as exc_info:
            module.main()

        assert exc_info.value.code == 0
        assert mock_urlopen.called

        captured_request = mock_urlopen.call_args[0][0]
        body = json.loads(captured_request.data.decode())
        assert body["method"] == "hamlet/event"
        assert body["params"]["hook_type"] == "TeammateIdle"


class TestTaskCompleted:
    def test_task_completed(self, monkeypatch):
        payload = {
            **BASE_PAYLOAD,
            "task_id": "t1",
            "task_subject": "test",
            "task_description": "desc",
            "teammate_name": "alice",
        }
        module = load_hook("task_completed")

        mock_urlopen = make_urlopen_mock()
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        monkeypatch.setattr(module, "find_server_url", lambda: SERVER_URL)
        monkeypatch.setattr(module, "find_config", lambda: (PROJECT_ID, PROJECT_NAME))
        monkeypatch.setattr(module.os, "chdir", lambda path: None)
        monkeypatch.setattr(module.os.path, "isdir", lambda path: True)
        monkeypatch.setattr(module.urllib.request, "urlopen", mock_urlopen)

        with pytest.raises(SystemExit) as exc_info:
            module.main()

        assert exc_info.value.code == 0
        assert mock_urlopen.called

        captured_request = mock_urlopen.call_args[0][0]
        body = json.loads(captured_request.data.decode())
        assert body["method"] == "hamlet/event"
        assert body["params"]["hook_type"] == "TaskCompleted"


class TestPostToolUseFailure:
    def test_post_tool_use_failure(self, monkeypatch):
        payload = {
            **BASE_PAYLOAD,
            "tool_name": "Read",
            "error": "failed",
            "is_interrupt": False,
        }
        module = load_hook("post_tool_use_failure")

        mock_urlopen = make_urlopen_mock()
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        monkeypatch.setattr(module, "find_server_url", lambda: SERVER_URL)
        monkeypatch.setattr(module, "find_config", lambda: (PROJECT_ID, PROJECT_NAME))
        monkeypatch.setattr(module.os, "chdir", lambda path: None)
        monkeypatch.setattr(module.os.path, "isdir", lambda path: True)
        monkeypatch.setattr(module.urllib.request, "urlopen", mock_urlopen)

        with pytest.raises(SystemExit) as exc_info:
            module.main()

        assert exc_info.value.code == 0
        assert mock_urlopen.called

        captured_request = mock_urlopen.call_args[0][0]
        body = json.loads(captured_request.data.decode())
        assert body["method"] == "hamlet/event"
        assert body["params"]["hook_type"] == "PostToolUseFailure"


class TestUserPromptSubmit:
    def test_user_prompt_submit(self, monkeypatch):
        payload = {**BASE_PAYLOAD, "prompt": "hello"}
        module = load_hook("user_prompt_submit")

        mock_urlopen = make_urlopen_mock()
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        monkeypatch.setattr(module, "find_server_url", lambda: SERVER_URL)
        monkeypatch.setattr(module, "find_config", lambda: (PROJECT_ID, PROJECT_NAME))
        monkeypatch.setattr(module.os, "chdir", lambda path: None)
        monkeypatch.setattr(module.os.path, "isdir", lambda path: True)
        monkeypatch.setattr(module.urllib.request, "urlopen", mock_urlopen)

        with pytest.raises(SystemExit) as exc_info:
            module.main()

        assert exc_info.value.code == 0
        assert mock_urlopen.called

        captured_request = mock_urlopen.call_args[0][0]
        body = json.loads(captured_request.data.decode())
        assert body["method"] == "hamlet/event"
        assert body["params"]["hook_type"] == "UserPromptSubmit"


class TestPreCompact:
    def test_pre_compact(self, monkeypatch):
        payload = {**BASE_PAYLOAD}
        module = load_hook("pre_compact")

        mock_urlopen = make_urlopen_mock()
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        monkeypatch.setattr(module, "find_server_url", lambda: SERVER_URL)
        monkeypatch.setattr(module, "find_config", lambda: (PROJECT_ID, PROJECT_NAME))
        monkeypatch.setattr(module.os, "chdir", lambda path: None)
        monkeypatch.setattr(module.os.path, "isdir", lambda path: True)
        monkeypatch.setattr(module.urllib.request, "urlopen", mock_urlopen)

        with pytest.raises(SystemExit) as exc_info:
            module.main()

        assert exc_info.value.code == 0
        assert mock_urlopen.called

        captured_request = mock_urlopen.call_args[0][0]
        body = json.loads(captured_request.data.decode())
        assert body["method"] == "hamlet/event"
        assert body["params"]["hook_type"] == "PreCompact"


class TestPostCompact:
    def test_post_compact(self, monkeypatch):
        payload = {**BASE_PAYLOAD}
        module = load_hook("post_compact")

        mock_urlopen = make_urlopen_mock()
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        monkeypatch.setattr(module, "find_server_url", lambda: SERVER_URL)
        monkeypatch.setattr(module, "find_config", lambda: (PROJECT_ID, PROJECT_NAME))
        monkeypatch.setattr(module.os, "chdir", lambda path: None)
        monkeypatch.setattr(module.os.path, "isdir", lambda path: True)
        monkeypatch.setattr(module.urllib.request, "urlopen", mock_urlopen)

        with pytest.raises(SystemExit) as exc_info:
            module.main()

        assert exc_info.value.code == 0
        assert mock_urlopen.called

        captured_request = mock_urlopen.call_args[0][0]
        body = json.loads(captured_request.data.decode())
        assert body["method"] == "hamlet/event"
        assert body["params"]["hook_type"] == "PostCompact"


class TestStopFailure:
    def test_stop_failure(self, monkeypatch):
        payload = {
            **BASE_PAYLOAD,
            "error": {"type": "internal", "reason": "crash"},
        }
        module = load_hook("stop_failure")

        mock_urlopen = make_urlopen_mock()
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        monkeypatch.setattr(module, "find_server_url", lambda: SERVER_URL)
        monkeypatch.setattr(module, "find_config", lambda: (PROJECT_ID, PROJECT_NAME))
        monkeypatch.setattr(module.os, "chdir", lambda path: None)
        monkeypatch.setattr(module.os.path, "isdir", lambda path: True)
        monkeypatch.setattr(module.urllib.request, "urlopen", mock_urlopen)

        with pytest.raises(SystemExit) as exc_info:
            module.main()

        assert exc_info.value.code == 0
        assert mock_urlopen.called

        captured_request = mock_urlopen.call_args[0][0]
        body = json.loads(captured_request.data.decode())
        assert body["method"] == "hamlet/event"
        assert body["params"]["hook_type"] == "StopFailure"

    def test_stop_failure_string_error(self, monkeypatch):
        """WI-291: StopFailure hook handles error field as string."""
        payload = {
            **BASE_PAYLOAD,
            "error": "Tool execution failed: exit code 1",
        }
        module = load_hook("stop_failure")

        mock_urlopen = make_urlopen_mock()
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        monkeypatch.setattr(module, "find_server_url", lambda: SERVER_URL)
        monkeypatch.setattr(module, "find_config", lambda: (PROJECT_ID, PROJECT_NAME))
        monkeypatch.setattr(module.os, "chdir", lambda path: None)
        monkeypatch.setattr(module.os.path, "isdir", lambda path: True)
        monkeypatch.setattr(module.urllib.request, "urlopen", mock_urlopen)

        with pytest.raises(SystemExit) as exc_info:
            module.main()

        assert exc_info.value.code == 0
        assert mock_urlopen.called

        captured_request = mock_urlopen.call_args[0][0]
        body = json.loads(captured_request.data.decode())
        assert body["method"] == "hamlet/event"
        assert body["params"]["hook_type"] == "StopFailure"
        assert body["params"]["error"]["type"] == "error"
        assert body["params"]["error"]["reason"] == "Tool execution failed: exit code 1"
