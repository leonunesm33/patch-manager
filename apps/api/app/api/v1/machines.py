from fastapi import APIRouter, HTTPException

from app.schemas.machine import Machine

router = APIRouter()

MOCK_MACHINES = [
    Machine(
        id="srv-web-01",
        name="SRV-WEB-01",
        ip="10.0.1.21",
        platform="Windows",
        group="Web Servers",
        status="online",
        pending_patches=4,
        last_check_in="2026-04-09T14:12:00Z",
        risk="critical",
    ),
    Machine(
        id="ubuntu-prod-03",
        name="ubuntu-prod-03",
        ip="10.1.4.33",
        platform="Ubuntu",
        group="Linux Production",
        status="online",
        pending_patches=3,
        last_check_in="2026-04-09T14:10:00Z",
        risk="important",
    ),
]


@router.get("", response_model=list[Machine])
def list_machines() -> list[Machine]:
    return MOCK_MACHINES


@router.get("/{machine_id}", response_model=Machine)
def get_machine(machine_id: str) -> Machine:
    for machine in MOCK_MACHINES:
        if machine.id == machine_id:
            return machine

    raise HTTPException(status_code=404, detail="Machine not found")
