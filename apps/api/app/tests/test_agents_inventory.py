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


def test_different_fingerprint_flags_conflict_but_still_updates_name(client, db_session):
    _post_inventory(client, hostname="srv-web-03", hardware_fingerprint="uuid-aaa")

    _post_inventory(client, hostname="srv-web-03-clone", hardware_fingerprint="uuid-bbb")

    machine = _get_machine(db_session)
    assert machine.name == "srv-web-03-clone"
    assert machine.hardware_fingerprint == "uuid-aaa"
    assert machine.identity_conflict_fingerprint == "uuid-bbb"
    assert machine.identity_conflict_detected_at is not None


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
