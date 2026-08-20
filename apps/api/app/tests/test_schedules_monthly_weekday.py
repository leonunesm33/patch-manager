from app.api.deps import require_operator
from app.main import app


class _FakeOperator:
    username = "test-operator"


def _base_payload(**overrides):
    payload = {
        "name": "Patch Tuesday",
        "scope_type": "os",
        "scope_value": "Windows",
        "install_date": "2026-01-01",
        "install_time": "02:00",
        "reboot_date": "2026-01-01",
        "reboot_time": "03:00",
        "recurrence": "monthly_weekday",
        "recurrence_weekday": 3,
        "recurrence_ordinal": 3,
        "reboot_policy": "if-needed",
        "is_active": True,
    }
    payload.update(overrides)
    return payload


def test_create_monthly_weekday_schedule(client):
    app.dependency_overrides[require_operator] = lambda: _FakeOperator()
    try:
        response = client.post("/api/v1/schedules", json=_base_payload())

        assert response.status_code == 201
        body = response.json()
        assert body["recurrence"] == "monthly_weekday"
        assert body["recurrence_weekday"] == 3
        assert body["recurrence_ordinal"] == 3
        assert "quinta-feira" in body["cron_label"]
        assert "3a" in body["cron_label"]
    finally:
        del app.dependency_overrides[require_operator]


def test_create_monthly_weekday_without_weekday_or_ordinal_is_rejected(client):
    app.dependency_overrides[require_operator] = lambda: _FakeOperator()
    try:
        response = client.post(
            "/api/v1/schedules",
            json=_base_payload(recurrence_weekday=None, recurrence_ordinal=None),
        )

        assert response.status_code == 422
    finally:
        del app.dependency_overrides[require_operator]


def test_create_monthly_weekday_with_invalid_weekday_is_rejected(client):
    app.dependency_overrides[require_operator] = lambda: _FakeOperator()
    try:
        response = client.post("/api/v1/schedules", json=_base_payload(recurrence_weekday=7))

        assert response.status_code == 422
    finally:
        del app.dependency_overrides[require_operator]


def test_create_monthly_weekday_with_invalid_ordinal_is_rejected(client):
    app.dependency_overrides[require_operator] = lambda: _FakeOperator()
    try:
        response = client.post("/api/v1/schedules", json=_base_payload(recurrence_ordinal=5))

        assert response.status_code == 422
    finally:
        del app.dependency_overrides[require_operator]


def test_switching_away_from_monthly_weekday_clears_weekday_and_ordinal(client):
    app.dependency_overrides[require_operator] = lambda: _FakeOperator()
    try:
        created = client.post("/api/v1/schedules", json=_base_payload()).json()

        response = client.put(
            f"/api/v1/schedules/{created['id']}",
            json=_base_payload(recurrence="weekly", recurrence_weekday=None, recurrence_ordinal=None),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["recurrence"] == "weekly"
        assert body["recurrence_weekday"] is None
        assert body["recurrence_ordinal"] is None
    finally:
        del app.dependency_overrides[require_operator]
