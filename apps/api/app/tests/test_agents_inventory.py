from datetime import UTC, datetime, timedelta

from app.api.deps import require_operator
from app.main import app
from app.services.settings_service import SettingsService
from app.tests.conftest import TEST_AGENT_ID


def _base_payload(**overrides):
    payload = {
        "agent_id": TEST_AGENT_ID,
        "platform": "linux",
        "hostname": "tpl-provisorio-01",
        "primary_ip": "10.0.0.5",
        "package_manager": "apt",
        "installed_packages": 100,
        "upgradable_packages": 0,
        "reboot_required": False,
        "os_name": "Linux",
        "os_version": "1",
        "kernel_version": "6.8.0",
        "agent_version": "0.2.0",
        "execution_mode": "dry-run",
    }
    payload.update(overrides)
    return payload


def _post_inventory(client, **overrides):
    return client.post("/api/v1/agents/inventory", json=_base_payload(**overrides))


def _get_machine(db_session):
    from app.models.machine import MachineModel

    return db_session.get(MachineModel, f"agent-{TEST_AGENT_ID}")


def test_creates_machine_with_hostname_and_fingerprint(client, db_session):
    response = _post_inventory(client, hardware_fingerprint="uuid-aaa")
    assert response.status_code == 200

    machine = _get_machine(db_session)
    assert machine.name == "tpl-provisorio-01"
    assert machine.hardware_fingerprint == "uuid-aaa"
    assert machine.identity_conflict_fingerprint is None
    assert machine.identity_conflict_detected_at is None


def test_hostname_rename_updates_name_without_conflict(client, db_session):
    _post_inventory(client, hostname="tpl-provisorio-01", hardware_fingerprint="uuid-aaa")

    _post_inventory(client, hostname="srv-web-03", hardware_fingerprint="uuid-aaa")

    machine = _get_machine(db_session)
    assert machine.name == "srv-web-03"
    assert machine.identity_conflict_fingerprint is None
    assert machine.identity_conflict_detected_at is None


def test_different_fingerprint_auto_resolves_on_first_change(client, db_session):
    _post_inventory(client, hostname="srv-web-03", hardware_fingerprint="uuid-aaa")

    _post_inventory(client, hostname="srv-web-03-clone", hardware_fingerprint="uuid-bbb")

    machine = _get_machine(db_session)
    assert machine.name == "srv-web-03-clone"
    assert machine.hardware_fingerprint == "uuid-bbb"
    assert machine.identity_conflict_fingerprint is None
    assert machine.identity_conflict_detected_at is None
    assert machine.identity_conflict_oscillation_detected_at is None
    assert machine.identity_conflict_previous_fingerprint == "uuid-aaa"
    assert machine.identity_conflict_auto_resolved_at is not None

    events = SettingsService(db_session).list_operational_events(limit=10)
    assert any(
        event["event_type"] == "machine_identity_conflict_auto_resolved"
        and "uuid-aaa" in event["summary"]
        and "uuid-bbb" in event["summary"]
        for event in events
    )


def test_fingerprint_flip_flop_within_window_is_flagged_as_oscillation(client, db_session):
    _post_inventory(client, hostname="srv-tpl-01", hardware_fingerprint="uuid-aaa")
    # Primeira mudanca: auto-resolve (comportamento normal de reprovisionamento).
    _post_inventory(client, hostname="srv-tpl-01", hardware_fingerprint="uuid-bbb")

    # Volta ao fingerprint anterior pouco depois: sinal de duas maquinas compartilhando
    # o mesmo agent_id, nao um reprovisionamento legitimo -> nao deve auto-resolver.
    _post_inventory(client, hostname="srv-tpl-01", hardware_fingerprint="uuid-aaa")

    machine = _get_machine(db_session)
    assert machine.hardware_fingerprint == "uuid-bbb"
    assert machine.identity_conflict_fingerprint == "uuid-aaa"
    assert machine.identity_conflict_detected_at is not None
    assert machine.identity_conflict_oscillation_detected_at is not None

    events = SettingsService(db_session).list_operational_events(limit=10)
    oscillation_event = next(
        event
        for event in events
        if event["event_type"] == "machine_identity_conflict_oscillation_detected"
    )
    assert oscillation_event["severity"] == "warn"
    assert "uuid-aaa" in oscillation_event["summary"]
    assert "uuid-bbb" in oscillation_event["summary"]


def test_return_after_oscillation_window_is_auto_resolved(client, db_session):
    _post_inventory(client, hostname="srv-tpl-window", hardware_fingerprint="uuid-aaa")
    _post_inventory(client, hostname="srv-tpl-window", hardware_fingerprint="uuid-bbb")

    machine = _get_machine(db_session)
    machine.identity_conflict_auto_resolved_at = datetime.now(UTC) - timedelta(hours=2)
    db_session.commit()

    _post_inventory(client, hostname="srv-tpl-window", hardware_fingerprint="uuid-aaa")

    machine = _get_machine(db_session)
    assert machine.hardware_fingerprint == "uuid-aaa"
    assert machine.identity_conflict_fingerprint is None
    assert machine.identity_conflict_oscillation_detected_at is None


def test_future_auto_resolved_timestamp_does_not_trigger_oscillation(client, db_session):
    _post_inventory(client, hostname="srv-tpl-future", hardware_fingerprint="uuid-aaa")
    _post_inventory(client, hostname="srv-tpl-future", hardware_fingerprint="uuid-bbb")

    machine = _get_machine(db_session)
    machine.identity_conflict_auto_resolved_at = datetime.now(UTC) + timedelta(hours=2)
    db_session.commit()

    _post_inventory(client, hostname="srv-tpl-future", hardware_fingerprint="uuid-aaa")

    machine = _get_machine(db_session)
    assert machine.hardware_fingerprint == "uuid-aaa"
    assert machine.identity_conflict_fingerprint is None
    assert machine.identity_conflict_oscillation_detected_at is None


def test_conflict_stays_flagged_for_manual_review_once_oscillation_detected(client, db_session):
    _post_inventory(client, hostname="srv-tpl-02", hardware_fingerprint="uuid-aaa")
    _post_inventory(client, hostname="srv-tpl-02", hardware_fingerprint="uuid-bbb")
    _post_inventory(client, hostname="srv-tpl-02", hardware_fingerprint="uuid-aaa")

    machine = _get_machine(db_session)
    assert machine.identity_conflict_oscillation_detected_at is not None

    # Mais um relato conflitante enquanto a oscilacao esta sinalizada: continua sem
    # auto-resolver, apenas atualiza o fingerprint visto por ultimo.
    _post_inventory(client, hostname="srv-tpl-02", hardware_fingerprint="uuid-ccc")

    machine = _get_machine(db_session)
    assert machine.hardware_fingerprint == "uuid-bbb"
    assert machine.identity_conflict_fingerprint == "uuid-ccc"
    assert machine.identity_conflict_oscillation_detected_at is not None


def test_manual_resolution_reenables_auto_resolution_on_next_sync(client, db_session):
    _post_inventory(client, hostname="srv-tpl-manual", hardware_fingerprint="uuid-aaa")
    _post_inventory(client, hostname="srv-tpl-manual", hardware_fingerprint="uuid-bbb")
    _post_inventory(client, hostname="srv-tpl-manual", hardware_fingerprint="uuid-aaa")

    app.dependency_overrides[require_operator] = lambda: type(
        "Operator", (), {"username": "test-operator"}
    )()
    try:
        response = client.post(
            f"/api/v1/machines/agent-{TEST_AGENT_ID}/resolve-identity-conflict"
        )
        assert response.status_code == 200
    finally:
        del app.dependency_overrides[require_operator]

    # A resolução manual promoveu uuid-aaa e limpou a memória de oscilação. Um novo
    # relato de uuid-bbb volta a ser tratado como reprovisionamento legítimo.
    _post_inventory(client, hostname="srv-tpl-manual", hardware_fingerprint="uuid-bbb")

    machine = _get_machine(db_session)
    assert machine.hardware_fingerprint == "uuid-bbb"
    assert machine.identity_conflict_fingerprint is None
    assert machine.identity_conflict_oscillation_detected_at is None
    assert machine.identity_conflict_previous_fingerprint == "uuid-aaa"
    assert machine.identity_conflict_auto_resolved_at is not None


def test_backfills_fingerprint_when_machine_had_none(client, db_session):
    _post_inventory(client, hostname="srv-legado-01")

    machine = _get_machine(db_session)
    assert machine.hardware_fingerprint is None

    _post_inventory(client, hostname="srv-legado-01", hardware_fingerprint="uuid-ccc")

    machine = _get_machine(db_session)
    assert machine.hardware_fingerprint == "uuid-ccc"
    assert machine.identity_conflict_fingerprint is None


def test_missing_fingerprint_never_triggers_conflict(client, db_session):
    _post_inventory(client, hostname="srv-antigo-01", hardware_fingerprint="uuid-ddd")

    _post_inventory(client, hostname="srv-antigo-01")

    machine = _get_machine(db_session)
    assert machine.hardware_fingerprint == "uuid-ddd"
    assert machine.identity_conflict_fingerprint is None


def test_repeat_report_same_hostname_and_fingerprint_is_noop(client, db_session):
    _post_inventory(client, hostname="srv-estavel-01", hardware_fingerprint="uuid-eee")

    _post_inventory(client, hostname="srv-estavel-01", hardware_fingerprint="uuid-eee")

    machine = _get_machine(db_session)
    assert machine.name == "srv-estavel-01"
    assert machine.hardware_fingerprint == "uuid-eee"
    assert machine.identity_conflict_fingerprint is None
    assert machine.identity_conflict_detected_at is None


def test_creates_machine_with_os_release(client, db_session):
    _post_inventory(client, hostname="srv-so-01", os_release="Ubuntu 24.04")

    machine = _get_machine(db_session)
    assert machine.os_release == "Ubuntu 24.04"


def test_os_release_updates_on_next_report(client, db_session):
    _post_inventory(client, hostname="srv-so-02", os_release="Ubuntu 22.04")

    _post_inventory(client, hostname="srv-so-02", os_release="Ubuntu 24.04")

    machine = _get_machine(db_session)
    assert machine.os_release == "Ubuntu 24.04"


def test_missing_os_release_does_not_clear_previous_value(client, db_session):
    _post_inventory(client, hostname="srv-so-03", os_release="Server 2022")

    _post_inventory(client, hostname="srv-so-03")

    machine = _get_machine(db_session)
    assert machine.os_release == "Server 2022"


def test_manual_group_reassignment_survives_next_inventory_report(client, db_session):
    _post_inventory(client, hostname="srv-grupo-01")

    machine = _get_machine(db_session)
    assert machine.group == "Agent Managed"
    machine.group = "Database"
    db_session.commit()

    _post_inventory(client, hostname="srv-grupo-01")

    machine = _get_machine(db_session)
    assert machine.group == "Database"
