from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Overridden at runtime by the DATABASE_URL environment variable injected
    # by Railway from the linked Postgres service.  The default below is only
    # used for local development; it intentionally uses the bare "postgres://"
    # scheme so that sync_database_url / async_database_url normalise it the
    # same way Railway's connection string is normalised.
    database_url: str = "postgres://postgres:postgres@localhost:5432/deepseek_chat"
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
