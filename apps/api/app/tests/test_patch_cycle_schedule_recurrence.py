import calendar
from datetime import UTC, date, datetime, time

from app.services.patch_cycle_service import PatchCycleService


def _nth_weekday_date(year: int, month: int, weekday: int, ordinal: int) -> date:
    """Calcula, de forma independente da implementacao testada, a data do
    dia da semana `weekday` (0=segunda) na posicao `ordinal` (1-4, ou -1
    para a ultima) dentro do mes informado."""
    _, days_in_month = calendar.monthrange(year, month)
    matches = [d for d in range(1, days_in_month + 1) if date(year, month, d).weekday() == weekday]
    if ordinal == -1:
        return date(year, month, matches[-1])
    return date(year, month, matches[ordinal - 1])


def _now_at(target_date: date, scheduled_time: str = "02:00") -> datetime:
    parsed = time.fromisoformat(scheduled_time)
    return datetime.combine(target_date, parsed, tzinfo=UTC)


def _service(db_session) -> PatchCycleService:
    return PatchCycleService(db_session)


def test_ordinal_of_weekday_in_month(db_session):
    service = _service(db_session)
    assert service._ordinal_of_weekday_in_month(date(2026, 8, 1)) == 1
    assert service._ordinal_of_weekday_in_month(date(2026, 8, 7)) == 1
    assert service._ordinal_of_weekday_in_month(date(2026, 8, 8)) == 2
    assert service._ordinal_of_weekday_in_month(date(2026, 8, 20)) == 3
    assert service._ordinal_of_weekday_in_month(date(2026, 8, 29)) == 5


def test_is_last_weekday_occurrence(db_session):
    service = _service(db_session)
    # Agosto/2026: quintas-feiras caem em 6, 13, 20, 27 — a de 27 e a ultima.
    assert service._is_last_weekday_occurrence(date(2026, 8, 27)) is True
    assert service._is_last_weekday_occurrence(date(2026, 8, 20)) is False


def test_third_thursday_of_month_matches(db_session):
    service = _service(db_session)
    third_thursday = _nth_weekday_date(2026, 8, 3, 3)  # 3 = quinta-feira (weekday)
    now = _now_at(third_thursday)

    assert service._is_schedule_window_due(
        "monthly_weekday",
        date(2026, 1, 1),
        "02:00",
        now,
        recurrence_weekday=3,
        recurrence_ordinal=3,
    ) is True


def test_second_thursday_does_not_match_third_thursday_schedule(db_session):
    service = _service(db_session)
    second_thursday = _nth_weekday_date(2026, 8, 3, 2)
    now = _now_at(second_thursday)

    assert service._is_schedule_window_due(
        "monthly_weekday",
        date(2026, 1, 1),
        "02:00",
        now,
        recurrence_weekday=3,
        recurrence_ordinal=3,
    ) is False


def test_wrong_weekday_does_not_match(db_session):
    service = _service(db_session)
    third_friday = _nth_weekday_date(2026, 8, 4, 3)  # 4 = sexta-feira
    now = _now_at(third_friday)

    assert service._is_schedule_window_due(
        "monthly_weekday",
        date(2026, 1, 1),
        "02:00",
        now,
        recurrence_weekday=3,  # quinta-feira esperada
        recurrence_ordinal=3,
    ) is False


def test_last_friday_matches_even_in_five_occurrence_month(db_session):
    service = _service(db_session)
    # Um mes com 5 sextas-feiras: a "ultima" (ordinal -1) deve bater na 5a, nao na 4a.
    last_friday = _nth_weekday_date(2027, 1, 4, -1)

    now = _now_at(last_friday)
    assert service._is_schedule_window_due(
        "monthly_weekday",
        date(2026, 1, 1),
        "02:00",
        now,
        recurrence_weekday=4,
        recurrence_ordinal=-1,
    ) is True


def test_fourth_friday_does_not_match_last_friday_schedule_in_five_friday_month(db_session):
    service = _service(db_session)
    fourth_friday = _nth_weekday_date(2027, 1, 4, 4)
    last_friday = _nth_weekday_date(2027, 1, 4, -1)
    assert fourth_friday != last_friday, "teste requer um mes com 5 sextas-feiras"

    now = _now_at(fourth_friday)
    assert service._is_schedule_window_due(
        "monthly_weekday",
        date(2026, 1, 1),
        "02:00",
        now,
        recurrence_weekday=4,
        recurrence_ordinal=-1,
    ) is False


def test_missing_weekday_or_ordinal_never_matches(db_session):
    service = _service(db_session)
    third_thursday = _nth_weekday_date(2026, 8, 3, 3)
    now = _now_at(third_thursday)

    assert service._is_schedule_window_due(
        "monthly_weekday", date(2026, 1, 1), "02:00", now, recurrence_weekday=None, recurrence_ordinal=3
    ) is False
    assert service._is_schedule_window_due(
        "monthly_weekday", date(2026, 1, 1), "02:00", now, recurrence_weekday=3, recurrence_ordinal=None
    ) is False


def test_does_not_fire_before_anchor_date(db_session):
    service = _service(db_session)
    third_thursday = _nth_weekday_date(2026, 8, 3, 3)
    now = _now_at(third_thursday)

    assert service._is_schedule_window_due(
        "monthly_weekday",
        date(2027, 1, 1),  # ancora no futuro
        "02:00",
        now,
        recurrence_weekday=3,
        recurrence_ordinal=3,
    ) is False
