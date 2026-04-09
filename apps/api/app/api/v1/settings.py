from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.schemas.auth import UserResponse
from app.schemas.settings import SettingsResponse, ToggleSetting

router = APIRouter()


@router.get("", response_model=SettingsResponse)
def get_settings(
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> SettingsResponse:
    return SettingsResponse(
        policy=[
            ToggleSetting(
                label="Patches criticos automaticos",
                description="Aplica patches criticos sem aprovacao manual.",
                enabled=True,
            ),
            ToggleSetting(
                label="Patches opcionais requerem aprovacao",
                description="Mantem o time no controle sobre updates nao obrigatorios.",
                enabled=True,
            ),
        ],
        notifications=[
            ToggleSetting(
                label="Notificar falhas",
                description="Envia alerta imediato quando uma execucao falha.",
                enabled=True,
            ),
            ToggleSetting(
                label="Relatorio semanal",
                description="Entrega uma visao executiva de conformidade.",
                enabled=False,
            ),
        ],
    )
