"""Проверка токена Яндекс SmartCaptcha."""
from __future__ import annotations

import httpx
from fastapi import HTTPException, status

from .config import get_settings


async def verify_smartcaptcha(token: str | None, ip: str | None) -> None:
    """Проверка токена Яндекс SmartCaptcha.

    Активна только если задан `smartcaptcha_server_key`. Иначе проверка пропускается.
    Недоступность сервиса капчи не блокирует запрос (fail-open).
    """
    server_key = get_settings().smartcaptcha_server_key.strip()
    if not server_key:
        return  # капча не настроена на сервере — не блокируем
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Подтвердите, что вы не робот"
        )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://smartcaptcha.yandexcloud.net/validate",
                data={"secret": server_key, "token": token, "ip": ip or ""},
            )
        ok = resp.status_code == 200 and resp.json().get("status") == "ok"
    except Exception:  # noqa: BLE001 — недоступность капчи не должна ронять запрос
        ok = True
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Проверка капчи не пройдена"
        )
