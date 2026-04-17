from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.agent_inventory_item import AgentInventoryItemModel


class AgentInventoryItemRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def replace_for_agent(
        self,
        agent_id: str,
        items: list[AgentInventoryItemModel],
    ) -> list[AgentInventoryItemModel]:
        self.session.execute(
            delete(AgentInventoryItemModel).where(AgentInventoryItemModel.agent_id == agent_id)
        )
        if items:
            self.session.add_all(items)
        self.session.commit()
        return self.list_for_agent(agent_id)

    def list_for_agent(self, agent_id: str) -> list[AgentInventoryItemModel]:
        statement = (
            select(AgentInventoryItemModel)
            .where(AgentInventoryItemModel.agent_id == agent_id)
            .order_by(
                AgentInventoryItemModel.item_type.asc(),
                AgentInventoryItemModel.sort_order.asc(),
                AgentInventoryItemModel.updated_at.desc(),
            )
        )
        return list(self.session.scalars(statement))

    def list_pending_for_agent(self, agent_id: str) -> list[AgentInventoryItemModel]:
        statement = (
            select(AgentInventoryItemModel)
            .where(
                AgentInventoryItemModel.agent_id == agent_id,
                AgentInventoryItemModel.item_type == "pending",
            )
            .order_by(AgentInventoryItemModel.sort_order.asc())
        )
        return list(self.session.scalars(statement))

    def list_installed_for_agent(self, agent_id: str) -> list[AgentInventoryItemModel]:
        statement = (
            select(AgentInventoryItemModel)
            .where(
                AgentInventoryItemModel.agent_id == agent_id,
                AgentInventoryItemModel.item_type == "installed",
            )
            .order_by(
                AgentInventoryItemModel.installed_at.desc().nullslast(),
                AgentInventoryItemModel.sort_order.asc(),
            )
        )
        return list(self.session.scalars(statement))
