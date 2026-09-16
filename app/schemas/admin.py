from pydantic import BaseModel, Field


class AuthClientCreateRequest(BaseModel):
    client_id: str = Field(min_length=3, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    redirect_uris: list[str] = Field(min_length=1)
    allowed_scopes: list[str] = Field(default_factory=lambda: ["openid", "profile", "email"])
    pkce_required: bool = True
    status: str = Field(default="active", max_length=32)
    client_secret: str | None = Field(default=None, min_length=8, max_length=255)


class AuthClientResponse(BaseModel):
    client_id: str
    name: str
    redirect_uris: list[str]
    allowed_scopes: list[str]
    pkce_required: bool
    status: str


class DailyDigestResponse(BaseModel):
    date: str
    timezone: str
    total_users: int
    users_created_today: int
    pageviews: int
    visitors: int
    visits: int
    umami_website_id: str
    feishu_sent: bool
