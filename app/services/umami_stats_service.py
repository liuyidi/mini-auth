"""Fetch Umami Cloud stats via public website Share token (no Pro API key)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import httpx

from app.config import settings


@dataclass(frozen=True)
class UmamiDayStats:
    website_id: str
    pageviews: int
    visitors: int
    visits: int


async def fetch_umami_day_stats(
    *,
    start: datetime,
    end: datetime,
    client: httpx.AsyncClient | None = None,
) -> UmamiDayStats:
    base = settings.umami_share_base_url.rstrip("/")
    slug = settings.umami_share_slug.strip()
    if not slug:
        raise ValueError("UMAMI_SHARE_SLUG is not configured")

    own_client = client is None
    http = client or httpx.AsyncClient(timeout=settings.digest_http_timeout_seconds)
    try:
        share_res = await http.get(f"{base}/api/share/{slug}")
        share_res.raise_for_status()
        share = share_res.json()
        token = share.get("token")
        website_id = share.get("websiteId")
        if not token or not website_id:
            raise ValueError("Umami share response missing token or websiteId")

        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)
        stats_res = await http.get(
            f"{base}/api/websites/{website_id}/stats",
            params={"startAt": start_ms, "endAt": end_ms},
            headers={
                "x-umami-share-token": token,
                "x-umami-share-context": "1",
            },
        )
        stats_res.raise_for_status()
        stats = stats_res.json()
        return UmamiDayStats(
            website_id=str(website_id),
            pageviews=int(stats.get("pageviews") or 0),
            visitors=int(stats.get("visitors") or 0),
            visits=int(stats.get("visits") or 0),
        )
    finally:
        if own_client:
            await http.aclose()
