from datetime import date

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.agent_credential import AgentCredentialModel
from app.models.machine_group import MachineGroupModel
from app.models.patch import PatchModel
from app.models.schedule import ScheduleModel
from app.models.user import UserModel


def seed_initial_data() -> None:
    session = SessionLocal()
    try:
        if session.scalar(select(UserModel.id).limit(1)) is None:
            session.add(
                UserModel(
                    id="user-admin",
                    username=settings.seed_admin_username,
                    full_name=settings.seed_admin_full_name,
                    password_hash=hash_password(settings.seed_admin_password),
                    role=settings.seed_admin_role,
                    is_active=True,
                    must_change_password=settings.seed_admin_force_password_change,
                    password_changed_at=None,
                )
            )

        if session.scalar(select(AgentCredentialModel.agent_id).limit(1)) is None:
            session.add(
                AgentCredentialModel(
                    agent_id=settings.seed_linux_agent_id,
                    platform="linux",
                    description=settings.seed_linux_agent_description,
                    key_hash=hash_password(settings.seed_linux_agent_key),
                    is_active=True,
                )
            )


        if session.scalar(select(MachineGroupModel.id).limit(1)) is None:
            session.add_all(
                [
                    MachineGroupModel(id="group-web-servers", name="Web Servers", description="Servidores web Windows."),
                    MachineGroupModel(id="group-database", name="Database", description="Servidores de banco de dados."),
                    MachineGroupModel(id="group-linux-production", name="Linux Production", description="Hosts Linux de producao."),
                    MachineGroupModel(id="group-agent-managed", name="Agent Managed", description="Hosts registrados automaticamente por agente."),
                ]
            )

        if session.scalar(select(PatchModel.id).limit(1)) is None:
            session.add_all(
                [
                    PatchModel(
                        id="KB5034441",
                        display_name="KB5034441",
                        target="Windows Servers",
                        severity="critical",
                        machines=8,
                        release_date=date(2026, 4, 8),
                        approval_status="pending",
                    ),
                    PatchModel(
                        id="openssl-3.0.2-0ubuntu1.14",
                        display_name="openssl 3.0.2-0ubuntu1.14",
                        target="Ubuntu Production",
                        severity="important",
                        machines=5,
                        release_date=date(2026, 4, 9),
                        approval_status="pending",
                    ),
                ]
            )

        if session.scalar(select(ScheduleModel.id).limit(1)) is None:
            session.add_all(
                [
                    ScheduleModel(
                        id="sched-1",
                        name="Janela Semanal Linux",
                        scope="SO: Linux",
                        scope_type="os",
                        scope_value="Linux",
                        cron_label="Semanal, 02:00",
                        install_time="02:00",
                        reboot_time="03:00",
                        recurrence="weekly",
                        reboot_policy="Reiniciar se necessario as 03:00",
                        is_active=False,
                    ),
                    ScheduleModel(
                        id="sched-2",
                        name="Patches Criticos Windows",
                        scope="SO: Windows",
                        scope_type="os",
                        scope_value="Windows",
                        cron_label="Diaria, 03:00",
                        install_time="03:00",
                        reboot_time="04:00",
                        recurrence="daily",
                        reboot_policy="Sempre reiniciar as 04:00",
                        is_active=False,
                    ),
                ]
            )

        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    seed_initial_data()
