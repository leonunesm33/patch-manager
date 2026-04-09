from fastapi import APIRouter

router = APIRouter()


@router.get("")
def get_settings() -> dict[str, object]:
    return {
        "policy": {
            "critical_auto": True,
            "optional_requires_approval": True,
        },
        "notifications": {
            "notify_failures": True,
            "weekly_report": False,
        },
    }
