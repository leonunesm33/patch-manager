import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from inventory import _collect_hardware_fingerprint  # noqa: E402


def test_override_env_var_takes_precedence(monkeypatch):
    _collect_hardware_fingerprint.cache_clear()
    monkeypatch.setenv("PATCH_MANAGER_FINGERPRINT_OVERRIDE", "forced-uuid-123")
    assert _collect_hardware_fingerprint() == "forced-uuid-123"


def test_returns_none_when_no_override_and_sudo_fails(monkeypatch):
    _collect_hardware_fingerprint.cache_clear()
    monkeypatch.delenv("PATCH_MANAGER_FINGERPRINT_OVERRIDE", raising=False)
    monkeypatch.setattr("inventory._run", lambda *args, **kwargs: "")
    assert _collect_hardware_fingerprint() is None
