from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Patch Manager API"
    app_env: str = "development"
    app_port: int = 8000
    database_url: str = (
        "postgresql+psycopg://patchmanager:patchmanager@localhost:5432/patchmanager"
    )
    jwt_secret: str = "changeme"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    seed_admin_username: str = "admin"
    seed_admin_password: str = "admin123"
    seed_admin_full_name: str = "Patch Manager Admin"
    cors_allow_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    cors_allow_origin_regex: str = r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"
    scheduler_autostart: bool = True
    scheduler_interval_seconds: int = 300
    worker_autostart: bool = True
    worker_interval_seconds: int = 30
    agent_bootstrap_token: str = "patch-manager-bootstrap-token"
    seed_linux_agent_id: str = "linux-agent-01"
    seed_linux_agent_key: str = "patch-manager-agent-key"
    seed_linux_agent_description: str = "Linux agent default credential"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allow_origins.split(",")
            if origin.strip()
        ]


settings = Settings()
