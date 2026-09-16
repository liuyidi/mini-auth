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
    jwt_issuer: str = "https://auth.liuyidi.me"
    jwt_audience: str = "mini-auth"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 30
    cors_origins: str = "*"
    auth_admin_api_key: str = ""
    email_provider: str = "aliyun_directmail"
    email_from: str = "Minibot <noreply@mail.liuyidi.me>"
    email_sender_domain: str = "mail.liuyidi.me"
    email_sender_account: str = "noreply"
    email_from_alias: str = "Minibot"
    email_template_login_code: str = "auth_login_code"
    email_code_ttl_seconds: int = 600
    email_code_resend_seconds: int = 60
    email_code_max_attempts: int = 5
    email_rate_limit_per_ip: int = 10
    email_rate_limit_per_email: int = 5
    email_rate_limit_window_seconds: int = 3600
    email_service_api_key: str = ""
    email_service_secret: str = ""
    email_service_region: str = "cn-hangzhou"
    email_debug_return_code: bool = False
    external_auth_allowed_return_origins: str = "https://auth.liuyidi.me"
    external_auth_context_expire_seconds: int = 600
    external_auth_cookie_secure: bool = True
    github_enabled: bool = False
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "https://auth.liuyidi.me/api/v1/auth/github/callback"
    github_http_timeout_seconds: float = 10.0
    google_enabled: bool = False
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "https://auth.liuyidi.me/api/v1/auth/google/callback"
    google_http_timeout_seconds: float = 10.0
    google_relay_url: str = ""
    google_relay_shared_secret: str = ""

    # Daily digest (Feishu) — Umami Cloud share API (no Pro API key)
    feishu_webhook_url: str = ""
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_target_open_id: str = ""
    feishu_target_id_type: str = "open_id"
    umami_share_base_url: str = "https://cloud.umami.is/analytics/us"
    umami_share_slug: str = "fAjwSKOBPqy37HAd"
    digest_timezone: str = "Asia/Shanghai"
    digest_http_timeout_seconds: float = 15.0

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
        if url.startswith("sqlite+aiosqlite://"):
            return url.replace("sqlite+aiosqlite://", "sqlite://", 1)
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def external_auth_allowed_return_origin_list(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.external_auth_allowed_return_origins.split(",")
            if origin.strip()
        ]


settings = Settings()
