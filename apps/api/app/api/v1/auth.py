from fastapi import APIRouter

router = APIRouter()


@router.post("/login")
def login() -> dict[str, str]:
    return {
        "access_token": "dev-token",
        "token_type": "bearer",
    }
