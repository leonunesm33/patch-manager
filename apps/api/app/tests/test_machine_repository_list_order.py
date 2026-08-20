from datetime import UTC, datetime

from app.models.machine import MachineModel
from app.repositories.machine_repository import MachineRepository


def _make_machine(machine_id: str, name: str) -> MachineModel:
    return MachineModel(
        id=machine_id,
        name=name,
        ip="10.0.0.1",
        platform="Ubuntu",
        environment="production",
        group="Agent Managed",
        status="online",
        pending_patches=0,
        last_check_in=datetime.now(UTC),
        risk="optional",
    )


def test_list_all_breaks_name_ties_deterministically_by_id(db_session):
    repository = MachineRepository(db_session)
    # Duas maquinas com o MESMO hostname (ex.: clone de template antes do
    # rename final): sem desempate por id, a ordem entre elas nao seria
    # garantida entre consultas, fazendo uma "sumir" da pagina no front.
    repository.add(_make_machine("agent-bbb", "tpl-provisorio-01"))
    repository.add(_make_machine("agent-aaa", "tpl-provisorio-01"))

    first_call = [machine.id for machine in repository.list_all()]
    second_call = [machine.id for machine in repository.list_all()]

    assert first_call == ["agent-aaa", "agent-bbb"]
    assert second_call == first_call
