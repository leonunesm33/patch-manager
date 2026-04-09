from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_patch_approvals() -> list[dict[str, object]]:
    return [
        {
            "id": "KB5034441",
            "target": "Windows Servers",
            "severity": "critical",
            "machines": 8,
            "release_date": "2026-04-08",
        },
        {
            "id": "openssl-3.0.2-0ubuntu1.14",
            "target": "Ubuntu Production",
            "severity": "important",
            "machines": 5,
            "release_date": "2026-04-09",
        },
    ]
