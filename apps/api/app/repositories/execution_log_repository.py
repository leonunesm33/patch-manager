from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.execution_log import ExecutionLogModel


class ExecutionLogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_recent(self, limit: int = 50) -> list[ExecutionLogModel]:
        statement = (
            select(ExecutionLogModel)
            .order_by(ExecutionLogModel.executed_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def add_many(self, logs: list[ExecutionLogModel]) -> list[ExecutionLogModel]:
        self.session.add_all(logs)
        self.session.commit()
        for log in logs:
            self.session.refresh(log)
        return logs
