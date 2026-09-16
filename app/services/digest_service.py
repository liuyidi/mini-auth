"""Build and optionally send the mini-auth daily ops digest."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.services.feishu_notify_service import send_feishu_card
from app.services.umami_stats_service import fetch_umami_day_stats

DEMO_EMAIL = "demo@mini-auth.dev"


@dataclass(frozen=True)
class DigestUserRow:
    email: str
    nickname: str
    created_at: str
    is_demo: bool


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
    users: list[DigestUserRow]
    feishu_sent: bool


def _day_bounds(tz_name: str) -> tuple[datetime, datetime, str]:
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end, start.date().isoformat()


def _format_created_at(value: datetime | None, tz_name: str) -> str:
    if value is None:
        return "-"
    tz = ZoneInfo(tz_name)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(tz).strftime("%Y-%m-%d %H:%M")


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


async def _list_users(db: AsyncSession, tz_name: str) -> list[DigestUserRow]:
    result = await db.execute(
        select(User.email, User.nickname, User.created_at)
        .where(User.deleted_at.is_(None))
        .order_by(User.created_at.asc())
    )
    rows: list[DigestUserRow] = []
    for email, nickname, created_at in result.all():
        normalized = str(email).strip().lower()
        is_demo = normalized == DEMO_EMAIL
        label = str(nickname or "")
        if is_demo and "demo" not in label.lower():
            label = f"{label}（demo）" if label else "demo"
        rows.append(
            DigestUserRow(
                email=str(email),
                nickname=label,
                created_at=_format_created_at(created_at, tz_name),
                is_demo=is_demo,
            )
        )
    return rows


def format_digest_text(digest: DailyDigest) -> str:
    lines = [
        f"mini-auth 日报（{digest.date} {digest.timezone}）",
        f"总用户：{digest.total_users}",
        f"今日新增用户：{digest.users_created_today}",
        f"今日 PV：{digest.pageviews}",
        f"今日访客：{digest.visitors}",
        f"今日访问：{digest.visits}",
        f"Umami：https://cloud.umami.is/share/{settings.umami_share_slug}",
        "",
        "邮箱 | 昵称 | 注册时间",
        "--- | --- | ---",
    ]
    for row in digest.users:
        mark = " · demo" if row.is_demo else ""
        lines.append(f"{row.email} | {row.nickname}{mark} | {row.created_at}")
    return "\n".join(lines)


def build_digest_card(digest: DailyDigest) -> dict[str, Any]:
    summary = (
        f"**总用户**：{digest.total_users}　"
        f"**今日新增**：{digest.users_created_today}\n"
        f"**今日 PV**：{digest.pageviews}　"
        f"**访客**：{digest.visitors}　"
        f"**访问**：{digest.visits}\n"
        f"[Umami 分享看板](https://cloud.umami.is/share/{settings.umami_share_slug})"
    )
    rows = [
        {
            "email": row.email,
            "nickname": row.nickname,
            "created_at": row.created_at,
        }
        for row in digest.users
    ]
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {
                "tag": "plain_text",
                "content": f"mini-auth 日报（{digest.date}）",
            },
        },
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": summary},
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**已注册用户（含 demo，共 {len(digest.users)}）**",
                },
            },
            {
                "tag": "table",
                "page_size": max(len(rows), 1),
                "row_height": "low",
                "header_style": {
                    "text_align": "left",
                    "text_size": "normal",
                    "background_style": "grey",
                    "text_color": "default",
                    "bold": True,
                    "lines": 1,
                },
                "columns": [
                    {
                        "name": "email",
                        "display_name": "邮箱",
                        "data_type": "text",
                        "horizontal_align": "left",
                        "width": "auto",
                    },
                    {
                        "name": "nickname",
                        "display_name": "昵称",
                        "data_type": "text",
                        "horizontal_align": "left",
                        "width": "auto",
                    },
                    {
                        "name": "created_at",
                        "display_name": "注册时间",
                        "data_type": "text",
                        "horizontal_align": "left",
                        "width": "auto",
                    },
                ],
                "rows": rows
                or [
                    {
                        "email": "-",
                        "nickname": "暂无用户",
                        "created_at": "-",
                    }
                ],
            },
        ],
    }


async def build_daily_digest(db: AsyncSession) -> DailyDigest:
    tz_name = settings.digest_timezone or "Asia/Shanghai"
    start, end, day = _day_bounds(tz_name)
    total_users, users_created_today = await _user_counts(db, start, end)
    users = await _list_users(db, tz_name)
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
        users=users,
        feishu_sent=False,
    )


async def run_daily_digest(db: AsyncSession, *, send: bool = True) -> DailyDigest:
    digest = await build_daily_digest(db)
    sent = False
    if send:
        await send_feishu_card(build_digest_card(digest))
        sent = True
    return DailyDigest(
        date=digest.date,
        timezone=digest.timezone,
        total_users=digest.total_users,
        users_created_today=digest.users_created_today,
        pageviews=digest.pageviews,
        visitors=digest.visitors,
        visits=digest.visits,
        umami_website_id=digest.umami_website_id,
        users=digest.users,
        feishu_sent=sent,
    )
