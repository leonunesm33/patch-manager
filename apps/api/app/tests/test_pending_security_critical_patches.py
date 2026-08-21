"""
Testes para o campo pending_security_critical_patches em dois pontos:

1. Recompute via POST /api/v1/agents/inventory (agents.py):
   - patches com category=="security" ou severity=="critical" incrementam o contador
   - patches com outra categoria/severidade não incrementam
   - o campo é zerado corretamente quando todos os patches são resolvidos

2. Decremento via PatchCycleService._complete_running_job (patch_cycle_service.py):
   - job concluído com patch security/critical decrementa o campo
   - job concluído com patch não-security/não-critical não decrementa
   - não vai abaixo de zero
"""
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from app.models.machine import MachineModel
from app.models.patch import PatchModel
from app.models.patch_job import PatchJobModel
from app.repositories.machine_repository import MachineRepository
from app.repositories.patch_job_repository import PatchJobRepository
from app.services.patch_cycle_service import PatchCycleService
from app.tests.conftest import TEST_AGENT_ID


# ---------------------------------------------------------------------------
# Helpers compartilhados
# ---------------------------------------------------------------------------

def _base_inventory_payload(**overrides):
    payload = {
        "agent_id": TEST_AGENT_ID,
        "platform": "linux",
        "hostname": "srv-test-sec",
        "primary_ip": "10.0.0.9",
        "package_manager": "apt",
        "installed_packages": 200,
        "upgradable_packages": 0,
        "reboot_required": False,
        "os_name": "Linux",
        "os_version": "1",
        "kernel_version": "6.8.0",
        "agent_version": "0.3.0",
        "execution_mode": "dry-run",
    }
    payload.update(overrides)
    return payload


def _post_inventory(client, pending_updates=None, **overrides):
    payload = _base_inventory_payload(**overrides)
    if pending_updates is not None:
        payload["pending_updates"] = pending_updates
    return client.post("/api/v1/agents/inventory", json=payload)


def _get_machine(db_session):
    return db_session.get(MachineModel, f"agent-{TEST_AGENT_ID}")


def _make_update(identifier, security_only=False, severity="important"):
    return {
        "identifier": identifier,
        "title": f"Update {identifier}",
        "source": "apt",
        "summary": "",
        "current_version": "1.0",
        "target_version": "1.1",
        "security_only": security_only,
        "severity": severity,
        "kb_id": None,
        "installed_at": None,
    }


# ---------------------------------------------------------------------------
# Testes do recompute em agents.py (via endpoint de inventário)
# ---------------------------------------------------------------------------

def test_recompute_counts_security_patches(client, db_session):
    """Patches com category=='security' devem incrementar o contador."""
    updates = [
        _make_update("pkg-sec-1", security_only=True),
        _make_update("pkg-sec-2", security_only=True),
        _make_update("pkg-other", security_only=False, severity="important"),
    ]
    r = _post_inventory(client, pending_updates=updates)
    assert r.status_code == 200

    machine = _get_machine(db_session)
    assert machine.pending_patches == 3
    assert machine.pending_security_critical_patches == 2


def test_recompute_counts_critical_severity_regardless_of_category(client, db_session):
    """Patches com severity=='critical' contam mesmo sem category=='security'."""
    updates = [
        _make_update("pkg-crit-1", security_only=False, severity="critical"),
        _make_update("pkg-low-1", security_only=False, severity="low"),
    ]
    r = _post_inventory(client, pending_updates=updates)
    assert r.status_code == 200

    machine = _get_machine(db_session)
    assert machine.pending_patches == 2
    assert machine.pending_security_critical_patches == 1


def test_recompute_security_and_critical_both_counted(client, db_session):
    """Security + critical juntos são contados sem duplicação."""
    updates = [
        _make_update("pkg-sec-crit", security_only=True, severity="critical"),
        _make_update("pkg-sec-only", security_only=True, severity="important"),
        _make_update("pkg-crit-only", security_only=False, severity="critical"),
        _make_update("pkg-other", security_only=False, severity="moderate"),
    ]
    r = _post_inventory(client, pending_updates=updates)
    assert r.status_code == 200

    machine = _get_machine(db_session)
    assert machine.pending_patches == 4
    assert machine.pending_security_critical_patches == 3


def test_recompute_zeroes_counter_when_no_security_critical_patches(client, db_session):
    """Quando não há patches security/critical, o contador deve ser 0."""
    updates = [
        _make_update("pkg-bugfix", security_only=False, severity="moderate"),
        _make_update("pkg-enhance", security_only=False, severity="low"),
    ]
    r = _post_inventory(client, pending_updates=updates)
    assert r.status_code == 200

    machine = _get_machine(db_session)
    assert machine.pending_patches == 2
    assert machine.pending_security_critical_patches == 0


def test_recompute_clears_counter_on_empty_inventory(client, db_session):
    """Após inventário sem pendências, ambos os contadores devem ser 0."""
    # Primeiro envia patches para popular
    _post_inventory(client, pending_updates=[_make_update("pkg-sec", security_only=True)])
    machine = _get_machine(db_session)
    assert machine.pending_patches > 0

    # Segundo envio sem pendências
    r = _post_inventory(client, pending_updates=[])
    assert r.status_code == 200

    machine = _get_machine(db_session)
    assert machine.pending_patches == 0
    assert machine.pending_security_critical_patches == 0


# ---------------------------------------------------------------------------
# Testes do decremento em PatchCycleService._complete_running_job
# ---------------------------------------------------------------------------

def _make_machine(db_session, pending=3, pending_sec_crit=2):
    machine = MachineModel(
        id=f"machine-{uuid4().hex[:8]}",
        name="test-host",
        ip="10.0.0.1",
        platform="Ubuntu",
        environment="production",
        group="test-group",
        status="online",
        pending_patches=pending,
        pending_security_critical_patches=pending_sec_crit,
        last_check_in=datetime.now(UTC),
        risk="important",
    )
    db_session.add(machine)
    db_session.commit()
    db_session.refresh(machine)
    return machine


def _make_patch(db_session, machine_id, category="bugfix", severity="important"):
    patch = PatchModel(
        id=f"patch-{uuid4().hex[:8]}",
        target=f"machine:{machine_id}",
        severity=severity,
        category=category,
        release_date=date.today(),
        approval_status="approved",
    )
    db_session.add(patch)
    db_session.commit()
    db_session.refresh(patch)
    return patch


def _make_schedule(db_session):
    """Retorna um objeto simples com os campos que PatchJobModel precisa — sem persistir no banco."""
    from types import SimpleNamespace
    return SimpleNamespace(id=f"sched-{uuid4().hex[:8]}", name="test-schedule")


def _make_job(db_session, machine, patch, schedule):
    job = PatchJobModel(
        id=f"job-{uuid4().hex[:8]}",
        schedule_id=schedule.id,
        schedule_name=schedule.name,
        machine_id=machine.id,
        machine_name=machine.name,
        patch_id=patch.id,
        platform=machine.platform,
        severity=patch.severity,
        status="running",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def _run_job(db_session, machine, patch):
    schedule = _make_schedule(db_session)
    job = _make_job(db_session, machine, patch, schedule)
    service = PatchCycleService(db_session)
    machines = MachineRepository(db_session).list_all()
    # list_all retorna todas; usar a lista completa como contexto do service
    from app.repositories.patch_repository import PatchRepository
    approved = [p for p in PatchRepository(db_session).list_all() if p.approval_status == "approved"]
    service._complete_running_job(job, pending_jobs_before=1, machines=machines, approved_patches=approved)
    db_session.refresh(machine)
    return machine


def test_decrement_security_patch_reduces_both_counters(db_session):
    """Concluir job de patch security deve decrementar pending e pending_sec_crit."""
    machine = _make_machine(db_session, pending=3, pending_sec_crit=2)
    patch = _make_patch(db_session, machine.id, category="security", severity="important")

    _run_job(db_session, machine, patch)

    assert machine.pending_patches == 2
    assert machine.pending_security_critical_patches == 1


def test_decrement_critical_patch_reduces_both_counters(db_session):
    """Concluir job de patch critical (não security) deve decrementar pending e pending_sec_crit."""
    machine = _make_machine(db_session, pending=4, pending_sec_crit=1)
    patch = _make_patch(db_session, machine.id, category="bugfix", severity="critical")

    _run_job(db_session, machine, patch)

    assert machine.pending_patches == 3
    assert machine.pending_security_critical_patches == 0


def test_decrement_non_security_non_critical_reduces_only_total(db_session):
    """Concluir job de patch bugfix/low NÃO deve tocar em pending_sec_crit."""
    machine = _make_machine(db_session, pending=5, pending_sec_crit=2)
    patch = _make_patch(db_session, machine.id, category="bugfix", severity="low")

    _run_job(db_session, machine, patch)

    assert machine.pending_patches == 4
    assert machine.pending_security_critical_patches == 2  # inalterado


def test_decrement_does_not_go_below_zero(db_session):
    """Decrementar com contador já em 0 não deve resultar em valor negativo."""
    machine = _make_machine(db_session, pending=1, pending_sec_crit=0)
    patch = _make_patch(db_session, machine.id, category="security", severity="critical")

    _run_job(db_session, machine, patch)

    assert machine.pending_patches == 0
    assert machine.pending_security_critical_patches == 0  # max(..., 0) protege
