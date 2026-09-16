"""Send ops alerts to Feishu (webhook or app IM)."""

from __future__ import annotations

import json

import httpx

from app.config import settings


async def _post_webhook(http: httpx.AsyncClient, text: str) -> None:
    url = settings.feishu_webhook_url.strip()
    response = await http.post(url, json={"msg_type": "text", "content": {"text": text}})
    response.raise_for_status()
    body = response.json() if response.content else {}
    if isinstance(body, dict) and body.get("code") not in (None, 0):
        raise RuntimeError(f"Feishu webhook error: {body}")


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


async def _post_app_text(http: httpx.AsyncClient, text: str) -> None:
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
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        },
    )
    response.raise_for_status()
    body = response.json() if response.content else {}
    if isinstance(body, dict) and body.get("code") not in (None, 0):
        raise RuntimeError(f"Feishu app message error: {body}")


async def send_feishu_text(text: str, *, client: httpx.AsyncClient | None = None) -> None:
    own_client = client is None
    http = client or httpx.AsyncClient(timeout=settings.digest_http_timeout_seconds)
    try:
        if settings.feishu_webhook_url.strip():
            await _post_webhook(http, text)
            return
        if (
            settings.feishu_app_id.strip()
            and settings.feishu_app_secret.strip()
            and settings.feishu_target_open_id.strip()
        ):
            await _post_app_text(http, text)
            return
        raise ValueError(
            "Feishu is not configured. Set FEISHU_WEBHOOK_URL or "
            "FEISHU_APP_ID/FEISHU_APP_SECRET/FEISHU_TARGET_OPEN_ID."
        )
    finally:
        if own_client:
            await http.aclose()
