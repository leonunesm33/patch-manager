from datetime import UTC, datetime

from app.api.deps import require_operator
from app.main import app
from app.models.machine import MachineModel


class _FakeOperator:
    username = "test-operator"


def _seed_machine_with_conflict(db_session, **overrides) -> MachineModel:
    fields = dict(
        id="agent-linux-clone-01",
        name="srv-clonado-01",
        ip="10.0.0.9",
        platform="Ubuntu",
        environment="production",
        group="Agent Managed",
        status="online",
        pending_patches=0,
        last_check_in=datetime.now(UTC),
        risk="optional",
        hardware_fingerprint="uuid-original",
        identity_conflict_fingerprint="uuid-conflitante",
        identity_conflict_detected_at=datetime.now(UTC),
    )
    fields.update(overrides)
    machine = MachineModel(**fields)
    db_session.add(machine)
    db_session.commit()
    return machine


def test_resolve_identity_conflict_accepts_latest_fingerprint_as_baseline(client, db_session):
    _seed_machine_with_conflict(db_session)
    app.dependency_overrides[require_operator] = lambda: _FakeOperator()

    response = client.post("/api/v1/machines/agent-linux-clone-01/resolve-identity-conflict")

    assert response.status_code == 200
    body = response.json()
    assert body["hardware_fingerprint"] == "uuid-conflitante"
    assert body["identity_conflict_fingerprint"] is None
    assert body["identity_conflict_detected_at"] is None

    db_session.expire_all()
    reloaded = db_session.get(MachineModel, "agent-linux-clone-01")
    assert reloaded.hardware_fingerprint == body["hardware_fingerprint"]
    assert reloaded.identity_conflict_fingerprint == body["identity_conflict_fingerprint"]
    assert reloaded.identity_conflict_detected_at == body["identity_conflict_detected_at"]

    del app.dependency_overrides[require_operator]


def test_resolve_identity_conflict_404_when_machine_missing(client):
    app.dependency_overrides[require_operator] = lambda: _FakeOperator()

    response = client.post("/api/v1/machines/does-not-exist/resolve-identity-conflict")

    assert response.status_code == 404

    del app.dependency_overrides[require_operator]


def test_resolve_identity_conflict_clears_oscillation_state(client, db_session):
    _seed_machine_with_conflict(
        db_session,
        identity_conflict_oscillation_detected_at=datetime.now(UTC),
        identity_conflict_auto_resolved_at=datetime.now(UTC),
        identity_conflict_previous_fingerprint="uuid-original",
    )
    app.dependency_overrides[require_operator] = lambda: _FakeOperator()

    response = client.post("/api/v1/machines/agent-linux-clone-01/resolve-identity-conflict")

    assert response.status_code == 200
    body = response.json()
    assert body["hardware_fingerprint"] == "uuid-conflitante"
    assert body["identity_conflict_fingerprint"] is None
    assert body["identity_conflict_detected_at"] is None
    assert body["identity_conflict_oscillation_detected_at"] is None
    assert body["identity_conflict_auto_resolved_at"] is None
    assert body["identity_conflict_previous_fingerprint"] is None

    del app.dependency_overrides[require_operator]


def test_resolve_identity_conflict_requires_pending_conflict(client, db_session):
    _seed_machine_with_conflict(
        db_session,
        identity_conflict_fingerprint=None,
        identity_conflict_detected_at=None,
        identity_conflict_auto_resolved_at=datetime.now(UTC),
        identity_conflict_previous_fingerprint="uuid-anterior",
    )
    app.dependency_overrides[require_operator] = lambda: _FakeOperator()

    response = client.post("/api/v1/machines/agent-linux-clone-01/resolve-identity-conflict")

    assert response.status_code == 409
    db_session.expire_all()
    reloaded = db_session.get(MachineModel, "agent-linux-clone-01")
    assert reloaded.identity_conflict_auto_resolved_at is not None
    assert reloaded.identity_conflict_previous_fingerprint == "uuid-anterior"

    del app.dependency_overrides[require_operator]
