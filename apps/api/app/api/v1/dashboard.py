from fastapi import APIRouter

from app.schemas.dashboard import (
    ActivityItem,
    DashboardResponse,
    DashboardSummary,
    PatchVolumeItem,
    PlatformDistribution,
)

router = APIRouter()


@router.get("", response_model=DashboardResponse)
def get_dashboard() -> DashboardResponse:
    return DashboardResponse(
        summary=DashboardSummary(
            monitored_machines=27,
            pending_patches=43,
            compliance_rate=94.0,
            failed_jobs=12,
        ),
        activity=[
            ActivityItem(
                title="KB5034441 aprovado para servidores web",
                detail="Scope: Windows Server Production",
                status="ok",
            ),
            ActivityItem(
                title="ubuntu-prod-03 aguardando janela de manutencao",
                detail="2 atualizacoes criticas pendentes",
                status="warn",
            ),
        ],
        patch_volume=[
            PatchVolumeItem(label="03/Abr", windows=8, linux=3),
            PatchVolumeItem(label="04/Abr", windows=5, linux=2),
            PatchVolumeItem(label="05/Abr", windows=12, linux=6),
            PatchVolumeItem(label="06/Abr", windows=3, linux=1),
            PatchVolumeItem(label="07/Abr", windows=9, linux=4),
            PatchVolumeItem(label="08/Abr", windows=14, linux=5),
            PatchVolumeItem(label="09/Abr", windows=7, linux=5),
        ],
        platform_distribution=PlatformDistribution(
            windows_servers=8,
            windows_workstations=11,
            linux_servers=8,
        ),
    )
