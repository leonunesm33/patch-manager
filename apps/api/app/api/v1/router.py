from fastapi import APIRouter

from app.api.v1 import agents, auth, dashboard, machines, patches, reports, schedules, settings

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(machines.router, prefix="/machines", tags=["machines"])
api_router.include_router(patches.router, prefix="/patches", tags=["patches"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
