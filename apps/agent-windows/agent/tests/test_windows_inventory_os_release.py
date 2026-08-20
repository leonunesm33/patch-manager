import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from inventory import _collect_os_release, _parse_windows_os_release  # noqa: E402


def test_parses_windows_server_caption():
    assert _parse_windows_os_release("Microsoft Windows Server 2022 Standard") == "Server 2022"


def test_parses_windows_server_datacenter_caption():
    assert _parse_windows_os_release("Microsoft Windows Server 2019 Datacenter") == "Server 2019"


def test_parses_windows_client_caption():
    assert _parse_windows_os_release("Microsoft Windows 11 Pro") == "11"


def test_returns_none_for_empty_caption():
    assert _parse_windows_os_release("") is None


def test_collect_returns_none_when_powershell_fails(monkeypatch):
    _collect_os_release.cache_clear()
    monkeypatch.setattr("inventory._run_powershell_json", lambda script: None)
    assert _collect_os_release() is None


def test_collect_uses_caption_from_powershell(monkeypatch):
    _collect_os_release.cache_clear()
    monkeypatch.setattr(
        "inventory._run_powershell_json",
        lambda script: {"caption": "Microsoft Windows Server 2022 Standard"},
    )
    assert _collect_os_release() == "Server 2022"
