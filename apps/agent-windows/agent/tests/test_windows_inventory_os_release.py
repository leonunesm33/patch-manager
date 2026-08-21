import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import inventory  # noqa: E402
from inventory import _collect_os_release, _parse_windows_os_release  # noqa: E402


def _reset_cache():
    """Reseta o cache manual de os_release entre testes."""
    inventory._os_release_cache = None
    inventory._os_release_collected = False


def test_parses_windows_server_caption():
    assert _parse_windows_os_release("Microsoft Windows Server 2022 Standard") == "Server 2022"


def test_parses_windows_server_datacenter_caption():
    assert _parse_windows_os_release("Microsoft Windows Server 2019 Datacenter") == "Server 2019"


def test_parses_windows_client_caption():
    assert _parse_windows_os_release("Microsoft Windows 11 Pro") == "11"


def test_returns_none_for_empty_caption():
    assert _parse_windows_os_release("") is None


def test_collect_returns_none_when_powershell_fails(monkeypatch):
    _reset_cache()
    monkeypatch.setattr("inventory._run_powershell_json", lambda script: None)
    assert _collect_os_release() is None


def test_collect_uses_caption_from_powershell(monkeypatch):
    _reset_cache()
    monkeypatch.setattr(
        "inventory._run_powershell_json",
        lambda script: {"caption": "Microsoft Windows Server 2022 Standard"},
    )
    assert _collect_os_release() == "Server 2022"


def test_collect_retries_after_failure(monkeypatch):
    """Falha na primeira chamada não deve cachear None — próxima tentativa deve funcionar."""
    _reset_cache()
    call_count = {"n": 0}

    def mock_powershell(script):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return None  # Simula falha na inicialização (ex: WMI ainda carregando)
        return {"caption": "Microsoft Windows Server 2022 Standard"}

    monkeypatch.setattr("inventory._run_powershell_json", mock_powershell)

    first = _collect_os_release()
    assert first is None  # Falha esperada na primeira chamada

    second = _collect_os_release()
    assert second == "Server 2022"  # Retry bem-sucedido na segunda chamada
    assert call_count["n"] == 2  # Confirma que houve duas chamadas ao PowerShell


def test_collect_caches_after_successful_collection(monkeypatch):
    """Após coleta bem-sucedida, o valor é cacheado e o PowerShell não é chamado novamente."""
    _reset_cache()
    call_count = {"n": 0}

    def mock_powershell(script):
        call_count["n"] += 1
        return {"caption": "Microsoft Windows 11 Pro"}

    monkeypatch.setattr("inventory._run_powershell_json", mock_powershell)

    first = _collect_os_release()
    second = _collect_os_release()

    assert first == "11"
    assert second == "11"
    assert call_count["n"] == 1  # PowerShell chamado apenas uma vez
