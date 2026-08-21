import os
import subprocess
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import _schedule_force_reidentify  # noqa: E402


def test_force_reidentify_schedules_initial_installer(monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 512, raising=False)
    monkeypatch.setattr("main.subprocess.Popen", lambda args, **kwargs: calls.append((args, kwargs)))
    new_agent_id = "windows-1234567890abcdef1234567890abcdef"
    command = {
        "id": "cmd-1",
        "command_type": "force_reidentify",
        "payload": {
            "server_url": "https://patch-manager.example.test",
            "bootstrap_token": "token with symbols/+",
            "new_agent_id": new_agent_id,
        },
    }

    result, message = _schedule_force_reidentify(command, SimpleNamespace())

    assert result == "applied"
    assert new_agent_id in message
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args[:4] == ["powershell.exe", "-ExecutionPolicy", "Bypass", "-NoProfile"]
    powershell_command = args[-1]
    assert "/api/v1/agents/install/windows.ps1?" in powershell_command
    assert f"agent_id={new_agent_id}" in powershell_command
    assert "bootstrap_token=token+with+symbols%2F%2B" in powershell_command
    assert kwargs["creationflags"] == 512


def test_force_reidentify_rejects_wrong_platform_agent_id(monkeypatch):
    monkeypatch.setattr("main.subprocess.Popen", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError()))
    result, message = _schedule_force_reidentify(
        {
            "payload": {
                "server_url": "https://patch-manager.example.test",
                "bootstrap_token": "token",
                "new_agent_id": "linux-1234567890abcdef1234567890abcdef",
            }
        },
        SimpleNamespace(),
    )
    assert result == "failed"
    assert "Windows" in message
