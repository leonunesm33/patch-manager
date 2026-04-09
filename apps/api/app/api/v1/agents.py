from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
def agent_status() -> dict[str, object]:
    return {
        "connected_agents": 0,
        "linux_ready": False,
        "windows_ready": False,
    }
