"""Send ops alerts to Feishu (webhook or app IM)."""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings


async def _tenant_access_token(http: httpx.AsyncClient) -> str:
    response = await http.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/",
        json={
            "app_id": settings.feishu_app_id.strip(),
            "app_secret": settings.feishu_app_secret.strip(),
        },
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("tenant_access_token")
    if not token:
        raise RuntimeError(f"Feishu token error: {payload}")
    return str(token)


async def _post_webhook_card(http: httpx.AsyncClient, card: dict[str, Any]) -> None:
    url = settings.feishu_webhook_url.strip()
    response = await http.post(url, json={"msg_type": "interactive", "card": card})
    response.raise_for_status()
    body = response.json() if response.content else {}
    if isinstance(body, dict) and body.get("code") not in (None, 0):
        raise RuntimeError(f"Feishu webhook error: {body}")


async def _post_app_card(http: httpx.AsyncClient, card: dict[str, Any]) -> None:
    token = await _tenant_access_token(http)
    receive_id_type = (settings.feishu_target_id_type or "open_id").strip()
    receive_id = settings.feishu_target_open_id.strip()
    response = await http.post(
        f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        json={
            "receive_id": receive_id,
            "msg_type": "interactive",
            "content": json.dumps(card, ensure_ascii=False),
        },
    )
    response.raise_for_status()
    body = response.json() if response.content else {}
    if isinstance(body, dict) and body.get("code") not in (None, 0):
        raise RuntimeError(f"Feishu app message error: {body}")


async def send_feishu_card(card: dict[str, Any], *, client: httpx.AsyncClient | None = None) -> None:
    own_client = client is None
    http = client or httpx.AsyncClient(timeout=settings.digest_http_timeout_seconds)
    try:
        if settings.feishu_webhook_url.strip():
            await _post_webhook_card(http, card)
            return
        if (
            settings.feishu_app_id.strip()
            and settings.feishu_app_secret.strip()
            and settings.feishu_target_open_id.strip()
        ):
            await _post_app_card(http, card)
            return
        raise ValueError(
            "Feishu is not configured. Set FEISHU_WEBHOOK_URL or "
            "FEISHU_APP_ID/FEISHU_APP_SECRET/FEISHU_TARGET_OPEN_ID."
        )
    finally:
        if own_client:
            await http.aclose()


async def send_feishu_text(text: str, *, client: httpx.AsyncClient | None = None) -> None:
    """Backward-compatible helper: wrap plain text into a simple card. """
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": "mini-auth 通知"},
        },
        "elements": [
            {"tag": "div", "text": {"tag": "plain_text", "content": text}},
        ],
    }
    await send_feishu_card(card, client=client)
