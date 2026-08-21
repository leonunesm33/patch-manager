from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.agent_command import AgentCommandModel


class AgentCommandRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, command_id: str) -> AgentCommandModel | None:
        return self.session.get(AgentCommandModel, command_id)

    def list_recent(self, limit: int = 50) -> list[AgentCommandModel]:
        statement = (
            select(AgentCommandModel)
            .order_by(AgentCommandModel.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def list_recent_for_agent(self, agent_id: str, limit: int = 20) -> list[AgentCommandModel]:
        statement = (
            select(AgentCommandModel)
            .where(AgentCommandModel.agent_id == agent_id)
            .order_by(AgentCommandModel.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def list_pending_for_agent(self, agent_id: str) -> list[AgentCommandModel]:
        statement = (
            select(AgentCommandModel)
            .where(
                AgentCommandModel.agent_id == agent_id,
                AgentCommandModel.status == "pending",
            )
            .order_by(AgentCommandModel.created_at.asc())
        )
        return list(self.session.scalars(statement))

    def add(self, command: AgentCommandModel) -> AgentCommandModel:
        self.session.add(command)
        self.session.commit()
        self.session.refresh(command)
        return command

    def has_active_force_reidentify(self, agent_id: str) -> bool:
        statement = select(AgentCommandModel.id).where(
            AgentCommandModel.agent_id == agent_id,
            AgentCommandModel.command_type == "force_reidentify",
            AgentCommandModel.status.in_(("pending", "running")),
        )
        return self.session.scalar(statement) is not None

    def expire_stale_force_reidentify(
        self,
        agent_id: str,
        stale_before: datetime,
    ) -> AgentCommandModel | None:
        statement = (
            select(AgentCommandModel)
            .where(
                AgentCommandModel.agent_id == agent_id,
                AgentCommandModel.command_type == "force_reidentify",
                AgentCommandModel.status == "running",
                AgentCommandModel.claimed_at < stale_before,
            )
            .order_by(AgentCommandModel.claimed_at.asc())
            .limit(1)
        )
        command = self.session.scalar(statement)
        if command is None:
            return None
        command.status = "failed"
        command.message = "Claim expirado sem confirmacao do agente."
        command.finished_at = datetime.now(UTC)
        self.session.add(command)
        self.session.commit()
        self.session.refresh(command)
        return command

    def claim_next_for_agent(self, agent_id: str) -> AgentCommandModel | None:
        next_id = (
            select(AgentCommandModel.id)
            .where(
                AgentCommandModel.agent_id == agent_id,
                AgentCommandModel.status == "pending",
            )
            .order_by(AgentCommandModel.created_at.asc(), AgentCommandModel.id.asc())
            .limit(1)
            .scalar_subquery()
        )
        statement = (
            update(AgentCommandModel)
            .where(
                AgentCommandModel.id == next_id,
                AgentCommandModel.status == "pending",
            )
            .values(status="running", claimed_at=datetime.now(UTC))
            .returning(AgentCommandModel)
        )
        command = self.session.scalars(statement).first()
        self.session.commit()
        return command

    def complete(self, command: AgentCommandModel, result: str, message: str | None) -> AgentCommandModel:
        if command.status != "running":
            return command
        normalized = result.strip().lower()
        command.status = "completed" if normalized == "applied" else "failed"
        command.message = message
        command.finished_at = datetime.now(UTC)
        self.session.add(command)
        self.session.commit()
        self.session.refresh(command)
        return command
