from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_credential import AgentCredentialModel


class AgentCredentialRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_agent_id(self, agent_id: str) -> AgentCredentialModel | None:
        return self.session.get(AgentCredentialModel, agent_id)

    def list_all(self) -> list[AgentCredentialModel]:
        statement = select(AgentCredentialModel).order_by(AgentCredentialModel.agent_id)
        return list(self.session.scalars(statement))

    def list_inactive(self) -> list[AgentCredentialModel]:
        statement = (
            select(AgentCredentialModel)
            .where(AgentCredentialModel.is_active.is_(False))
            .order_by(AgentCredentialModel.agent_id)
        )
        return list(self.session.scalars(statement))

    def add(self, credential: AgentCredentialModel) -> AgentCredentialModel:
        self.session.add(credential)
        self.session.commit()
        self.session.refresh(credential)
        return credential

    def update(self, credential: AgentCredentialModel) -> AgentCredentialModel:
        self.session.add(credential)
        self.session.commit()
        self.session.refresh(credential)
        return credential
