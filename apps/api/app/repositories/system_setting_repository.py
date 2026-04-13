from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.system_setting import SystemSettingModel


class SystemSettingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, key: str) -> SystemSettingModel | None:
        return self.session.get(SystemSettingModel, key)

    def list_by_prefix(self, prefix: str) -> list[SystemSettingModel]:
        statement = select(SystemSettingModel).where(SystemSettingModel.key.startswith(prefix))
        return list(self.session.scalars(statement))

    def upsert(self, key: str, value: str) -> SystemSettingModel:
        setting = self.get(key)
        if setting is None:
            setting = SystemSettingModel(key=key, value=value)
        else:
            setting.value = value

        self.session.add(setting)
        self.session.commit()
        self.session.refresh(setting)
        return setting
