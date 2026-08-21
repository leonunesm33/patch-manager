import os
import sys
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import _schedule_force_reidentify  # noqa: E402


def test_force_reidentify_schedules_initial_installer(monkeypatch):
    calls = []
    monkeypatch.setattr("main.subprocess.Popen", lambda args, **kwargs: calls.append((args, kwargs)))
    command = {
        "id": "cmd-1",
        "command_type": "force_reidentify",
        "payload": {
            "server_url": "https://patch-manager.example.test",
            "bootstrap_token": "token with symbols/+",
            "new_agent_id": "linux-1234567890abcdef1234567890abcdef",
        },
    }

    result, message = _schedule_force_reidentify(command, SimpleNamespace())

    assert result == "applied"
    assert "linux-1234567890abcdef1234567890abcdef" in message
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args[:2] == ["bash", "-c"]
    shell_command = args[2]
    assert "/api/v1/agents/install/linux.sh?" in shell_command
    installer_url = shell_command.split("curl -fsSL ", 1)[1].split(" | sudo bash", 1)[0].strip("'")
    query = parse_qs(urlparse(installer_url).query)
    assert query["agent_id"] == ["linux-1234567890abcdef1234567890abcdef"]
    assert query["bootstrap_token"] == ["token with symbols/+"]
    assert kwargs["start_new_session"] is True


def test_force_reidentify_rejects_missing_bootstrap_token(monkeypatch):
    monkeypatch.setattr("main.subprocess.Popen", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))
    result, message = _schedule_force_reidentify(
        {
            "payload": {
                "server_url": "https://patch-manager.example.test",
                "new_agent_id": "linux-1234567890abcdef1234567890abcdef",
            }
        },
        SimpleNamespace(),
    )
    assert result == "failed"
    assert "bootstrap_token" in message
