from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session

from app.models.patch_job import PatchJobModel


class PatchJobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_recent(self, limit: int = 50) -> list[PatchJobModel]:
        statement = select(PatchJobModel).order_by(PatchJobModel.created_at.desc()).limit(limit)
        return list(self.session.scalars(statement))

    def list_recent_for_machine(self, machine_id: str, limit: int = 20) -> list[PatchJobModel]:
        statement = (
            select(PatchJobModel)
            .where(PatchJobModel.machine_id == machine_id)
            .order_by(PatchJobModel.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def get_by_id(self, job_id: str) -> PatchJobModel | None:
        return self.session.get(PatchJobModel, job_id)

    def list_pending(self) -> list[PatchJobModel]:
        statement = (
            select(PatchJobModel)
            .where(PatchJobModel.status == "pending")
            .order_by(PatchJobModel.created_at.asc())
        )
        return list(self.session.scalars(statement))

    def list_running(self) -> list[PatchJobModel]:
        statement = (
            select(PatchJobModel)
            .where(PatchJobModel.status == "running")
            .order_by(PatchJobModel.started_at.asc())
        )
        return list(self.session.scalars(statement))

    def get_next_pending_for_platform(self, platform: str) -> PatchJobModel | None:
        platform_normalized = platform.lower()
        statement = (
            select(PatchJobModel)
            .where(
                PatchJobModel.status == "pending",
                PatchJobModel.claimed_by_agent.is_(None),
            )
            .order_by(PatchJobModel.created_at.asc())
        )
        for job in self.session.scalars(statement):
            job_platform = job.platform.lower()
            if platform_normalized == "linux" and job_platform in {"ubuntu", "debian", "rhel", "linux"}:
                return job
            if platform_normalized == job_platform:
                return job
        return None

    def add_many(self, jobs: list[PatchJobModel]) -> list[PatchJobModel]:
        self.session.add_all(jobs)
        self.session.commit()
        for job in jobs:
            self.session.refresh(job)
        return jobs

    def update(self, job: PatchJobModel) -> PatchJobModel:
        self.session.add(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def exists_open_job(self, schedule_id: str, machine_id: str, patch_id: str) -> bool:
        statement: Select[tuple[int]] = select(func.count(PatchJobModel.id)).where(
            and_(
                PatchJobModel.schedule_id == schedule_id,
                PatchJobModel.machine_id == machine_id,
                PatchJobModel.patch_id == patch_id,
                PatchJobModel.status.in_(("pending", "running")),
            )
        )
        return bool(self.session.scalar(statement))
