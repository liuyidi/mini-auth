from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps_admin import require_admin_api_key
from app.schemas.admin import (
    AuthClientCreateRequest,
    AuthClientResponse,
    DailyDigestResponse,
    DigestUserRowResponse,
)
from app.services.admin_service import create_auth_client, list_auth_clients
from app.services.digest_service import build_daily_digest, run_daily_digest

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_api_key)])


def _to_response(digest) -> DailyDigestResponse:
    users = []
    for row in digest.users:
        payload = row if isinstance(row, dict) else row.__dict__
        users.append(DigestUserRowResponse(**payload))
    return DailyDigestResponse(
        date=digest.date,
        timezone=digest.timezone,
        total_users=digest.total_users,
        users_created_today=digest.users_created_today,
        pageviews=digest.pageviews,
        visitors=digest.visitors,
        visits=digest.visits,
        umami_website_id=digest.umami_website_id,
        users=users,
        feishu_sent=digest.feishu_sent,
    )


@router.post("/clients", response_model=AuthClientResponse, status_code=201)
async def create_client(
    body: AuthClientCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthClientResponse:
    return await create_auth_client(db, body)


@router.get("/clients", response_model=list[AuthClientResponse])
async def get_clients(db: AsyncSession = Depends(get_db)) -> list[AuthClientResponse]:
    return await list_auth_clients(db)


@router.get("/stats", response_model=DailyDigestResponse)
async def get_stats(db: AsyncSession = Depends(get_db)) -> DailyDigestResponse:
    """Preview digest metrics without sending Feishu."""
    try:
        digest = await build_daily_digest(db)
    except Exception as exc:  # noqa: BLE001 — surface Umami/network errors to admin caller
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return _to_response(digest)


@router.post("/daily-digest", response_model=DailyDigestResponse)
async def post_daily_digest(
    db: AsyncSession = Depends(get_db),
    send: bool = Query(default=True, description="Set false to preview without Feishu"),
) -> DailyDigestResponse:
    try:
        digest = await run_daily_digest(db, send=send)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return _to_response(digest)
