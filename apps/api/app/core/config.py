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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
