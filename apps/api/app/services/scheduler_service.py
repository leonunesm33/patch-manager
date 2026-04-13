from __future__ import annotations

from datetime import datetime
from threading import Lock

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.database import SessionLocal
from app.schemas.worker import (
    PatchCycleRunResponse,
    PatchJobProcessResponse,
    SchedulerStatusResponse,
)
from app.services.patch_cycle_service import PatchCycleService


class SchedulerService:
    def __init__(self) -> None:
        self._scheduler = BackgroundScheduler(timezone="UTC")
        self._enqueue_job_id = "patch-enqueue"
        self._worker_job_id = "patch-worker"
        self._lock = Lock()
        self._last_enqueue_run_at: datetime | None = None
        self._last_worker_run_at: datetime | None = None
        self._last_enqueue_result: PatchCycleRunResponse | None = None
        self._last_worker_result: PatchJobProcessResponse | None = None

    def start(self) -> SchedulerStatusResponse:
        with self._lock:
            if not self._scheduler.running:
                self._scheduler.start()

            if self._scheduler.get_job(self._enqueue_job_id) is None:
                self._scheduler.add_job(
                    self._enqueue_cycle_job,
                    "interval",
                    seconds=settings.scheduler_interval_seconds,
                    id=self._enqueue_job_id,
                    replace_existing=True,
                )
            if self._scheduler.get_job(self._worker_job_id) is None:
                self._scheduler.add_job(
                    self._process_queue_job,
                    "interval",
                    seconds=settings.worker_interval_seconds,
                    id=self._worker_job_id,
                    replace_existing=True,
                )

        return self.status()

    def stop(self) -> SchedulerStatusResponse:
        with self._lock:
            if self._scheduler.running:
                self._scheduler.shutdown(wait=False)
                self._scheduler = BackgroundScheduler(timezone="UTC")

        return self.status()

    def trigger_now(self) -> PatchCycleRunResponse:
        result = self._enqueue_cycle_job()
        return result

    def status(self) -> SchedulerStatusResponse:
        enqueue_job = self._scheduler.get_job(self._enqueue_job_id) if self._scheduler.running else None
        worker_job = self._scheduler.get_job(self._worker_job_id) if self._scheduler.running else None
        return SchedulerStatusResponse(
            running=self._scheduler.running and enqueue_job is not None and worker_job is not None,
            enqueue_interval_seconds=settings.scheduler_interval_seconds,
            worker_interval_seconds=settings.worker_interval_seconds,
            next_enqueue_run_at=enqueue_job.next_run_time.isoformat()
            if enqueue_job and enqueue_job.next_run_time
            else None,
            next_worker_run_at=worker_job.next_run_time.isoformat()
            if worker_job and worker_job.next_run_time
            else None,
            last_enqueue_run_at=self._last_enqueue_run_at.isoformat() if self._last_enqueue_run_at else None,
            last_worker_run_at=self._last_worker_run_at.isoformat() if self._last_worker_run_at else None,
            last_enqueue_result=self._last_enqueue_result,
            last_worker_result=self._last_worker_result,
        )

    def _enqueue_cycle_job(self) -> PatchCycleRunResponse:
        session = SessionLocal()
        try:
            service = PatchCycleService(session)
            result = service.enqueue_jobs()
            self._last_enqueue_run_at = datetime.utcnow()
            self._last_enqueue_result = result
            return result
        finally:
            session.close()

    def _process_queue_job(self) -> PatchJobProcessResponse:
        session = SessionLocal()
        try:
            service = PatchCycleService(session)
            result = service.process_pending_jobs()
            self._last_worker_run_at = datetime.utcnow()
            self._last_worker_result = result
            return result
        finally:
            session.close()


scheduler_service = SchedulerService()
