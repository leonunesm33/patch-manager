import json
from datetime import UTC, datetime

from app.api.deps import require_operator
from app.main import app
from app.models.agent_command import AgentCommandModel
from app.models.machine import MachineModel
from app.repositories.agent_identity_history_repository import AgentIdentityHistoryRepository
from app.services.agent_registry_service import agent_registry_service
from app.services.settings_service import SettingsService
from app.tests.conftest import TEST_AGENT_ID


class _FakeOperator:
    username = "test-operator"


def _connect_shared_agent() -> None:
    agent_registry_service.check_in(
        TEST_AGENT_ID,
        "linux",
        "clone-host-a",
        "Linux",
        "Ubuntu 24.04",
        "6.8.0",
        "0.2.0",
        "apply",
    )


def test_force_reidentify_enqueues_claims_and_tracks_new_enrollment(client, db_session):
    _connect_shared_agent()
    app.dependency_overrides[require_operator] = lambda: _FakeOperator()
    settings = SettingsService(db_session)
    settings.set_agent_bootstrap_token("valid-bootstrap-token", expires_in_days=30)
    settings.set_agent_install_server_url("https://patch-manager.example.test")
    db_session.add(
        MachineModel(
            id=f"agent-{TEST_AGENT_ID}",
            name="clone-host-a",
            ip="10.0.0.10",
            platform="Ubuntu",
            environment="production",
            group="Agent Managed",
            status="warning",
            pending_patches=0,
            last_check_in=datetime.now(UTC),
            risk="important",
            hardware_fingerprint="fingerprint-a",
            identity_conflict_fingerprint="fingerprint-b",
            identity_conflict_detected_at=datetime.now(UTC),
            identity_conflict_oscillation_detected_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    try:
        response = client.post(
            f"/api/v1/agents/connected/{TEST_AGENT_ID}/force-reidentify",
            json={"reason": "shared template identity"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "queued"
        assert body["old_agent_id"] == TEST_AGENT_ID
        assert body["new_agent_id"].startswith("linux-")
        assert body["target_semantics"] == "next_claimant"

        command = db_session.get(AgentCommandModel, body["command_id"])
        assert command is not None
        assert command.command_type == "force_reidentify"
        assert command.status == "pending"
        command_payload = json.loads(command.payload_json)
        assert command_payload["server_url"] == "https://patch-manager.example.test"
        assert command_payload["bootstrap_token"] == "valid-bootstrap-token"
        assert command_payload["new_agent_id"] == body["new_agent_id"]
        assert command_payload["target_semantics"] == "next_claimant"

        duplicate = client.post(
            f"/api/v1/agents/connected/{TEST_AGENT_ID}/force-reidentify",
            json={"reason": "must wait for first claimant"},
        )
        assert duplicate.status_code == 409

        claimed = client.post(
            "/api/v1/agents/commands/next",
            json={"agent_id": TEST_AGENT_ID, "platform": "linux"},
        )
        assert claimed.status_code == 200
        assert claimed.json()["id"] == body["command_id"]
        assert claimed.json()["payload"]["new_agent_id"] == body["new_agent_id"]

        no_second_claim = client.post(
            "/api/v1/agents/commands/next",
            json={"agent_id": TEST_AGENT_ID, "platform": "linux"},
        )
        assert no_second_claim.status_code == 200
        assert no_second_claim.json() is None

        result = client.post(
            f"/api/v1/agents/commands/{body['command_id']}/result",
            json={
                "agent_id": TEST_AGENT_ID,
                "result": "applied",
                "message": "installer scheduled",
            },
        )
        assert result.status_code == 200
        db_session.refresh(command)
        assert command.status == "completed"

        enrollment = client.post(
            "/api/v1/agents/enroll",
            headers={"x-bootstrap-token": "valid-bootstrap-token"},
            json={
                "agent_id": body["new_agent_id"],
                "platform": "linux",
                "hostname": "clone-host-b",
                "primary_ip": "10.0.0.11",
                "os_name": "Linux",
                "os_version": "Ubuntu 24.04",
                "kernel_version": "6.8.0",
                "agent_version": "0.2.0",
            },
        )
        assert enrollment.status_code == 200
        assert enrollment.json()["status"] == "pending"

        history = AgentIdentityHistoryRepository(db_session).list_for_agent(TEST_AGENT_ID, limit=20)
        history_types = {item.event_type for item in history}
        assert {
            "force_reidentify_requested",
            "force_reidentify_claimed",
            "force_reidentify_installer_scheduled",
            "force_reidentify_enrollment_detected",
        }.issubset(history_types)
        enrollment_event = next(
            item for item in history if item.event_type == "force_reidentify_enrollment_detected"
        )
        assert enrollment_event.hostname == "clone-host-b"
        assert enrollment_event.new_agent_id == body["new_agent_id"]
    finally:
        agent_registry_service.disconnect(TEST_AGENT_ID)
        app.dependency_overrides.pop(require_operator, None)


def test_force_reidentify_rejects_expired_bootstrap_token(client, db_session):
    _connect_shared_agent()
    app.dependency_overrides[require_operator] = lambda: _FakeOperator()
    settings = SettingsService(db_session)
    settings.set_agent_bootstrap_token("expired-token", expires_in_days=30)
    settings.repository.upsert(
        settings.AGENT_BOOTSTRAP_TOKEN_EXPIRES_AT_KEY,
        "2000-01-01T00:00:00+00:00",
    )

    try:
        response = client.post(
            f"/api/v1/agents/connected/{TEST_AGENT_ID}/force-reidentify",
            json={},
        )
        assert response.status_code == 409
        assert "expired" in response.json()["detail"].lower()
    finally:
        agent_registry_service.disconnect(TEST_AGENT_ID)
        app.dependency_overrides.pop(require_operator, None)


def test_reidentify_installers_use_reserved_agent_id_and_restart_service():
    from app.api.v1.agents import (
        _build_linux_installer_script,
        _build_windows_installer_script,
    )

    linux_id = "linux-1234567890abcdef1234567890abcdef"
    linux_script = _build_linux_installer_script(
        "https://patch-manager.example.test",
        "bootstrap-token",
        linux_id,
    )
    assert f'AGENT_ID="{linux_id}"' in linux_script
    assert 'systemctl restart "${SERVICE_NAME}"' in linux_script

    windows_id = "windows-1234567890abcdef1234567890abcdef"
    windows_script = _build_windows_installer_script(
        "https://patch-manager.example.test",
        "bootstrap-token",
        windows_id,
    )
    assert f'$AgentId = "{windows_id}"' in windows_script
    assert "reidentify-staging" in windows_script
    assert "reidentify-backup" in windows_script
    assert "Move-Item -Path $StagingRoot -Destination $FinalInstallRoot" in windows_script
    assert "Move-Item -Path $BackupRoot -Destination $FinalInstallRoot" in windows_script
    assert "Stop-Service -Name $ServiceName -Force" in windows_script
    assert "if ($null -eq $ExistingService)" in windows_script
    assert "Start-Service -Name $ServiceName" in windows_script
    assert windows_script.rindex("Save-UrlFile -Url") < windows_script.index(
        "Stop-Service -Name $ServiceName -Force"
    )


def test_command_result_replay_is_idempotent_and_conflicts_are_rejected(client, db_session):
    command = AgentCommandModel(
        id="cmd-replay",
        agent_id=TEST_AGENT_ID,
        command_type="force_reidentify",
        status="running",
        requested_by="test-operator",
        payload_json=json.dumps(
            {
                "new_agent_id": "linux-1234567890abcdef1234567890abcdef",
                "reason": "test",
            }
        ),
    )
    db_session.add(command)
    db_session.commit()

    payload = {
        "agent_id": TEST_AGENT_ID,
        "result": "applied",
        "message": "installer scheduled",
    }
    first = client.post("/api/v1/agents/commands/cmd-replay/result", json=payload)
    replay = client.post("/api/v1/agents/commands/cmd-replay/result", json=payload)
    conflict = client.post(
        "/api/v1/agents/commands/cmd-replay/result",
        json={**payload, "result": "failed"},
    )

    assert first.status_code == 200
    assert replay.status_code == 200
    assert conflict.status_code == 409
    history = AgentIdentityHistoryRepository(db_session).list_for_agent(TEST_AGENT_ID, limit=20)
    assert sum(item.event_type == "force_reidentify_installer_scheduled" for item in history) == 1


def test_unknown_command_result_does_not_create_reboot_event(client, db_session):
    db_session.add(
        AgentCommandModel(
            id="cmd-unknown",
            agent_id=TEST_AGENT_ID,
            command_type="future_command",
            status="running",
            requested_by="test-operator",
            payload_json="{}",
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/agents/commands/cmd-unknown/result",
        json={
            "agent_id": TEST_AGENT_ID,
            "result": "failed",
            "message": "unsupported locally",
        },
    )

    assert response.status_code == 200
    events = SettingsService(db_session).list_operational_events(limit=20)
    assert any(item["event_type"] == "unsupported_agent_command_result" for item in events)
    assert not any(item["event_type"] == "manual_reboot_failed" for item in events)
