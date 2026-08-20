import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from inventory import _collect_os_release, _parse_os_release  # noqa: E402


def test_parses_name_and_version_id():
    content = 'NAME="Ubuntu"\nVERSION_ID="24.04"\nPRETTY_NAME="Ubuntu 24.04.1 LTS"\n'
    assert _parse_os_release(content) == "Ubuntu 24.04"


def test_falls_back_to_pretty_name_when_version_id_missing():
    content = 'NAME="Debian GNU/Linux"\nPRETTY_NAME="Debian GNU/Linux 12 (bookworm)"\n'
    assert _parse_os_release(content) == "Debian GNU/Linux 12 (bookworm)"


def test_returns_none_for_empty_content():
    assert _parse_os_release("") is None


def test_collect_returns_none_when_file_missing(monkeypatch):
    _collect_os_release.cache_clear()

    def _raise_open(*args, **kwargs):
        raise OSError("not found")

    monkeypatch.setattr("builtins.open", _raise_open)
    assert _collect_os_release() is None
