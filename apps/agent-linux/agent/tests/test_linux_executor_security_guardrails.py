import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from executor import execute_patch_job_with_mode  # noqa: E402


def _base_job(**overrides):
    job = {
        "patch_id": "nginx@agent-1",
        "real_apply_enabled": True,
        "severity": "moderate",
    }
    job.update(overrides)
    return job


def _patch_common(monkeypatch, has_security_candidate: bool):
    monkeypatch.setattr("executor._check_upgrade_needed", lambda package_name: True)
    monkeypatch.setattr("executor._has_security_candidate", lambda package_name: has_security_candidate)
    monkeypatch.setattr("executor._is_reboot_required", lambda: False)
    monkeypatch.setattr("executor._run", lambda *args, **kwargs: (0, "ok"))


def test_critical_severity_bypasses_security_tag_requirement(monkeypatch):
    _patch_common(monkeypatch, has_security_candidate=False)
    job = _base_job(allow_security_and_critical=True, severity="critical")

    result, _error, _ = execute_patch_job_with_mode(job, "apply", None)

    assert result == "applied"


def test_non_critical_without_security_tag_is_blocked(monkeypatch):
    _patch_common(monkeypatch, has_security_candidate=False)
    job = _base_job(allow_security_and_critical=True, severity="moderate")

    result, error, _ = execute_patch_job_with_mode(job, "apply", None)

    assert result == "failed"
    assert "does not have a security-tagged or critical-severity" in error


def test_non_critical_with_security_tag_is_allowed(monkeypatch):
    _patch_common(monkeypatch, has_security_candidate=True)
    job = _base_job(allow_security_and_critical=True, severity="moderate")

    result, _error, _ = execute_patch_job_with_mode(job, "apply", None)

    assert result == "applied"


def test_guardrail_disabled_allows_any_severity(monkeypatch):
    _patch_common(monkeypatch, has_security_candidate=False)
    job = _base_job(allow_security_and_critical=False, severity="low")

    result, _error, _ = execute_patch_job_with_mode(job, "apply", None)

    assert result == "applied"
