from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.agent_identity_history import AgentIdentityHistoryModel


class AgentIdentityHistoryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, event: AgentIdentityHistoryModel) -> AgentIdentityHistoryModel:
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event

    def add_once_for_command(
        self,
        event: AgentIdentityHistoryModel,
    ) -> AgentIdentityHistoryModel:
        if event.command_id is not None:
            existing = self.get_command_event(event.command_id, event.event_type)
            if existing is not None:
                return existing
        return self.add(event)

    def get_command_event(
        self,
        command_id: str,
        event_type: str,
    ) -> AgentIdentityHistoryModel | None:
        statement = select(AgentIdentityHistoryModel).where(
            AgentIdentityHistoryModel.command_id == command_id,
            AgentIdentityHistoryModel.event_type == event_type,
        )
        return self.session.scalar(statement)

    def get_requested_transition_by_new_agent_id(
        self,
        new_agent_id: str,
    ) -> AgentIdentityHistoryModel | None:
        statement = (
            select(AgentIdentityHistoryModel)
            .where(
                AgentIdentityHistoryModel.new_agent_id == new_agent_id,
                AgentIdentityHistoryModel.event_type == "force_reidentify_requested",
            )
            .order_by(AgentIdentityHistoryModel.occurred_at.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def list_for_agent(
        self,
        agent_id: str,
        limit: int = 30,
    ) -> list[AgentIdentityHistoryModel]:
        statement = (
            select(AgentIdentityHistoryModel)
            .where(
                or_(
                    AgentIdentityHistoryModel.agent_id == agent_id,
                    AgentIdentityHistoryModel.new_agent_id == agent_id,
                )
            )
            .order_by(AgentIdentityHistoryModel.occurred_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))
