from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.schemas.auth import UserResponse
router = APIRouter()


@router.get("/status")
def agent_status(
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> dict[str, object]:
    return {
        "connected_agents": 0,
        "linux_ready": False,
        "windows_ready": False,
    }
