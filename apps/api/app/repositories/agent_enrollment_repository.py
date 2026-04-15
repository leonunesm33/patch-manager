from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_enrollment import AgentEnrollmentModel


class AgentEnrollmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_agent_id(self, agent_id: str) -> AgentEnrollmentModel | None:
        return self.session.get(AgentEnrollmentModel, agent_id)

    def list_pending(self) -> list[AgentEnrollmentModel]:
        statement = (
            select(AgentEnrollmentModel)
            .where(AgentEnrollmentModel.status == "pending")
            .order_by(AgentEnrollmentModel.requested_at.desc())
        )
        return list(self.session.scalars(statement))

    def list_rejected(self) -> list[AgentEnrollmentModel]:
        statement = (
            select(AgentEnrollmentModel)
            .where(AgentEnrollmentModel.status == "rejected")
            .order_by(AgentEnrollmentModel.requested_at.desc())
        )
        return list(self.session.scalars(statement))

    def upsert_request(
        self,
        *,
        agent_id: str,
        platform: str,
        hostname: str,
        primary_ip: str,
        os_name: str,
        os_version: str,
        kernel_version: str,
        agent_version: str,
    ) -> AgentEnrollmentModel:
        enrollment = self.get_by_agent_id(agent_id)
        if enrollment is None:
            enrollment = AgentEnrollmentModel(
                agent_id=agent_id,
                platform=platform,
                hostname=hostname,
                primary_ip=primary_ip,
                os_name=os_name,
                os_version=os_version,
                kernel_version=kernel_version,
                agent_version=agent_version,
                status="pending",
            )
        else:
            enrollment.platform = platform
            enrollment.hostname = hostname
            enrollment.primary_ip = primary_ip
            enrollment.os_name = os_name
            enrollment.os_version = os_version
            enrollment.kernel_version = kernel_version
            enrollment.agent_version = agent_version
            if enrollment.status == "active":
                enrollment.status = "pending"
                enrollment.issued_key = None
                enrollment.approved_at = None

        self.session.add(enrollment)
        self.session.commit()
        self.session.refresh(enrollment)
        return enrollment

    def approve(self, enrollment: AgentEnrollmentModel, issued_key: str) -> AgentEnrollmentModel:
        enrollment.status = "approved"
        enrollment.issued_key = issued_key
        enrollment.approved_at = datetime.now(UTC)
        self.session.add(enrollment)
        self.session.commit()
        self.session.refresh(enrollment)
        return enrollment

    def mark_active(self, enrollment: AgentEnrollmentModel) -> AgentEnrollmentModel:
        enrollment.status = "active"
        enrollment.issued_key = None
        self.session.add(enrollment)
        self.session.commit()
        self.session.refresh(enrollment)
        return enrollment

    def reject(self, enrollment: AgentEnrollmentModel) -> AgentEnrollmentModel:
        enrollment.status = "rejected"
        enrollment.issued_key = None
        enrollment.approved_at = None
        self.session.add(enrollment)
        self.session.commit()
        self.session.refresh(enrollment)
        return enrollment

    def reopen_pending(self, enrollment: AgentEnrollmentModel) -> AgentEnrollmentModel:
        enrollment.status = "pending"
        enrollment.issued_key = None
        enrollment.approved_at = None
        self.session.add(enrollment)
        self.session.commit()
        self.session.refresh(enrollment)
        return enrollment
