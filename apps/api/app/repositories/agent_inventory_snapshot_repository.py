from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_inventory_snapshot import AgentInventorySnapshotModel


class AgentInventorySnapshotRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_agent_id(self, agent_id: str) -> AgentInventorySnapshotModel | None:
        return self.session.get(AgentInventorySnapshotModel, agent_id)

    def list_recent(self, limit: int = 50) -> list[AgentInventorySnapshotModel]:
        statement = (
            select(AgentInventorySnapshotModel)
            .order_by(AgentInventorySnapshotModel.updated_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def list_all(self) -> list[AgentInventorySnapshotModel]:
        statement = select(AgentInventorySnapshotModel).order_by(
            AgentInventorySnapshotModel.updated_at.desc()
        )
        return list(self.session.scalars(statement))

    def upsert(self, snapshot: AgentInventorySnapshotModel) -> AgentInventorySnapshotModel:
        existing = self.get_by_agent_id(snapshot.agent_id)
        if existing is None:
            self.session.add(snapshot)
        else:
            existing.platform = snapshot.platform
            existing.hostname = snapshot.hostname
            existing.primary_ip = snapshot.primary_ip
            existing.package_manager = snapshot.package_manager
            existing.installed_packages = snapshot.installed_packages
            existing.upgradable_packages = snapshot.upgradable_packages
            existing.reboot_required = snapshot.reboot_required
            existing.installed_update_count = snapshot.installed_update_count
            existing.pending_update_summary = snapshot.pending_update_summary
            existing.windows_update_source = snapshot.windows_update_source
            existing.os_name = snapshot.os_name
            existing.os_version = snapshot.os_version
            existing.kernel_version = snapshot.kernel_version
            existing.agent_version = snapshot.agent_version
            existing.execution_mode = snapshot.execution_mode
            self.session.add(existing)
        self.session.commit()
        stored = self.get_by_agent_id(snapshot.agent_id)
        if stored is None:
            raise RuntimeError("Agent inventory snapshot was not persisted")
        return stored
