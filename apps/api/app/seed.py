from datetime import UTC, date, datetime

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.machine import MachineModel
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
                    is_active=True,
                )
            )

        if session.scalar(select(MachineModel.id).limit(1)) is None:
            session.add_all(
                [
                    MachineModel(
                        id="srv-web-01",
                        name="SRV-WEB-01",
                        ip="10.0.1.21",
                        platform="Windows",
                        group="Web Servers",
                        status="online",
                        pending_patches=4,
                        last_check_in=datetime(2026, 4, 9, 14, 12, tzinfo=UTC),
                        risk="critical",
                    ),
                    MachineModel(
                        id="srv-db-02",
                        name="SRV-DB-02",
                        ip="10.0.2.11",
                        platform="Windows",
                        group="Database",
                        status="warning",
                        pending_patches=7,
                        last_check_in=datetime(2026, 4, 9, 13, 58, tzinfo=UTC),
                        risk="critical",
                    ),
                    MachineModel(
                        id="ubuntu-prod-03",
                        name="ubuntu-prod-03",
                        ip="10.1.4.33",
                        platform="Ubuntu",
                        group="Linux Production",
                        status="online",
                        pending_patches=3,
                        last_check_in=datetime(2026, 4, 9, 14, 10, tzinfo=UTC),
                        risk="important",
                    ),
                ]
            )

        if session.scalar(select(PatchModel.id).limit(1)) is None:
            session.add_all(
                [
                    PatchModel(
                        id="KB5034441",
                        target="Windows Servers",
                        severity="critical",
                        machines=8,
                        release_date=date(2026, 4, 8),
                    ),
                    PatchModel(
                        id="openssl-3.0.2-0ubuntu1.14",
                        target="Ubuntu Production",
                        severity="important",
                        machines=5,
                        release_date=date(2026, 4, 9),
                    ),
                ]
            )

        if session.scalar(select(ScheduleModel.id).limit(1)) is None:
            session.add_all(
                [
                    ScheduleModel(
                        id="sched-1",
                        name="Janela Semanal Linux",
                        scope="Ubuntu Production",
                        cron_label="Toda quarta, 02:00",
                        reboot_policy="Somente se necessario",
                    ),
                    ScheduleModel(
                        id="sched-2",
                        name="Patches Criticos Windows",
                        scope="Windows Servers",
                        cron_label="Diariamente, 03:00",
                        reboot_policy="Sempre reiniciar",
                    ),
                ]
            )

        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    seed_initial_data()
