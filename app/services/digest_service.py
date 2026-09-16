"""Build and optionally send the mini-auth daily ops digest."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.services.feishu_notify_service import send_feishu_text
from app.services.umami_stats_service import fetch_umami_day_stats


@dataclass(frozen=True)
class DailyDigest:
    date: str
    timezone: str
    total_users: int
    users_created_today: int
    pageviews: int
    visitors: int
    visits: int
    umami_website_id: str
    feishu_sent: bool


def _day_bounds(tz_name: str) -> tuple[datetime, datetime, str]:
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end, start.date().isoformat()


async def _user_counts(db: AsyncSession, start: datetime, end: datetime) -> tuple[int, int]:
    start_utc = start.astimezone(timezone.utc)
    end_utc = end.astimezone(timezone.utc)

    total = await db.scalar(
        select(func.count()).select_from(User).where(User.deleted_at.is_(None))
    )
    created_today = await db.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.deleted_at.is_(None),
            User.created_at >= start_utc,
            User.created_at < end_utc,
        )
    )
    return int(total or 0), int(created_today or 0)


def format_digest_text(digest: DailyDigest) -> str:
    return (
        f"mini-auth 日报（{digest.date} {digest.timezone}）\n"
        f"总用户：{digest.total_users}\n"
        f"今日新增用户：{digest.users_created_today}\n"
        f"今日 PV：{digest.pageviews}\n"
        f"今日访客：{digest.visitors}\n"
        f"今日访问：{digest.visits}\n"
        f"Umami：https://cloud.umami.is/share/{settings.umami_share_slug}"
    )


async def build_daily_digest(db: AsyncSession) -> DailyDigest:
    tz_name = settings.digest_timezone or "Asia/Shanghai"
    start, end, day = _day_bounds(tz_name)
    total_users, users_created_today = await _user_counts(db, start, end)
    umami = await fetch_umami_day_stats(start=start, end=end)
    return DailyDigest(
        date=day,
        timezone=tz_name,
        total_users=total_users,
        users_created_today=users_created_today,
        pageviews=umami.pageviews,
        visitors=umami.visitors,
        visits=umami.visits,
        umami_website_id=umami.website_id,
        feishu_sent=False,
    )


async def run_daily_digest(db: AsyncSession, *, send: bool = True) -> DailyDigest:
    digest = await build_daily_digest(db)
    sent = False
    if send:
        await send_feishu_text(format_digest_text(digest))
        sent = True
    return DailyDigest(**{**asdict(digest), "feishu_sent": sent})
