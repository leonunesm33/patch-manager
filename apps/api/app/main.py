from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.limiter import limiter
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestIDMiddleware
from app.services.scheduler_service import scheduler_service

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("startup", environment=settings.app_env)
    if settings.scheduler_autostart:
        scheduler_service.start()
        logger.info("scheduler_started")
    try:
        yield
    finally:
        if scheduler_service.status().running:
            scheduler_service.stop()
            logger.info("scheduler_stopped")
        logger.info("shutdown")


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

# Rate limiter state and error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware — order matters: RequestID first (outermost), then SlowAPI, then CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestIDMiddleware)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/detailed")
def health_check_detailed() -> dict[str, object]:
    database_status = "ok"
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
    except Exception:
        database_status = "error"

    scheduler_status = scheduler_service.status()
    return {
        "status": "ok" if database_status == "ok" else "degraded",
        "environment": settings.app_env,
        "database": database_status,
        "scheduler": {
            "running": scheduler_status.running,
            "last_enqueue_run_at": scheduler_status.last_enqueue_run_at,
            "last_worker_run_at": scheduler_status.last_worker_run_at,
        },
    }
