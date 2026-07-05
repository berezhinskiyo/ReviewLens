"""Фабрика payments-роутера (Т-Банк).

Общее для всех проектов — контракт webhook: проверка подписи Token и ответ телом "OK"
(иначе Т-Банк повторяет уведомление). Проектная логика (какой тариф, как активировать
подписку) передаётся через callbacks.
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .. import tinkoff

logger = logging.getLogger("authbilling.payments")

# create_payment(db, user, payload) -> (confirmation_url, payment_id)
CreatePayment = Callable[[AsyncSession, Any, dict], Awaitable[tuple[str, Any]]]
# handle_success(db, payload) — вызывается только после успешной проверки Token
HandleSuccess = Callable[[AsyncSession, dict], Awaitable[None]]


def make_payments_router(
    *,
    get_db: Callable[..., Any],
    handle_success: HandleSuccess,
    create_payment: CreatePayment | None = None,
    get_current_user: Callable[..., Any] | None = None,
    route_prefix: str = "/api/payments",
    tags: list[str] | None = None,
) -> APIRouter:
    router = APIRouter(prefix=route_prefix, tags=tags or ["payments"])

    if create_payment is not None:
        if get_current_user is None:
            raise ValueError("get_current_user обязателен, если задан create_payment")

        @router.post("")
        async def create(
            payload: dict,
            user: Any = Depends(get_current_user),
            db: AsyncSession = Depends(get_db),
        ):
            try:
                confirmation_url, payment_id = await create_payment(db, user, payload)
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
            return {"confirmation_url": confirmation_url, "payment_id": payment_id}

    @router.post("/webhook")
    async def webhook(request: Request, db: AsyncSession = Depends(get_db)) -> PlainTextResponse:
        """Уведомление Т-Банка. Без auth — доверие по подписи Token."""
        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bad payload")

        logger.info("tinkoff.webhook.received status=%s", payload.get("Status"))
        if not tinkoff.verify_notification(payload):
            logger.warning("tinkoff.webhook.bad_token")
            return PlainTextResponse("OK")  # не раскрываем причину; Т-Банк ждёт OK

        if payload.get("Success") and str(payload.get("Status", "")) in tinkoff.SUCCESS_STATUSES:
            await handle_success(db, payload)
        return PlainTextResponse("OK")

    return router
