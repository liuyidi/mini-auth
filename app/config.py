from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Railway injects DATABASE_URL as "postgres://..." — both that prefix and
    # the standard "postgresql://..." prefix are normalised by the properties
    # below.  The default here is only used for local development.
    database_url: str = "postgresql://postgres:postgres@localhost:5432/deepseek_chat"
    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 30
    cors_origins: str = "*"

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    @property
    def sync_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql://", 1)
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
