from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_reports() -> list[dict[str, str]]:
    return [
        {
            "date": "09/04 14:10",
            "machine": "SRV-WEB-01",
            "patch": "KB5034441",
            "platform": "Windows",
            "severity": "critical",
            "result": "applied",
            "duration": "4m 12s",
        }
    ]
