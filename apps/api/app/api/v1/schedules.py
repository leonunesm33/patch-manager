from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_schedules() -> list[dict[str, str]]:
    return [
        {
            "id": "sched-1",
            "name": "Janela Semanal Linux",
            "scope": "Ubuntu Production",
            "cron_label": "Toda quarta, 02:00",
            "reboot_policy": "Somente se necessario",
        }
    ]
