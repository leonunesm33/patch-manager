from pydantic import BaseModel


class LinuxExecutionModeUpdate(BaseModel):
    linux_agent_mode: str
    machine_group: str | None = None
