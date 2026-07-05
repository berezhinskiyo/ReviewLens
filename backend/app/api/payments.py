"""Оплата подписки (Т-Банк) поверх общего пакета auth-billing-core.

Контракт webhook (проверка подписи Token + ответ «OK») берётся из фабрики
`make_payments_router`; проектная логика (тарифы, активация подписки) — в
`app.services.payment`.
"""
from typing import Any

from authbilling import make_payments_router
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import Payment, User
from app.db.session import get_db
from app.schemas.api import PaymentOut
from app.services.payment import PaymentError, create_payment, handle_webhook


async def _create_payment(db: AsyncSession, user: User, payload: dict) -> tuple[str, Any]:
    plan = payload.get("plan")
    period_months = int(payload.get("period_months", 1))
    try:
        payment, confirmation_url = await create_payment(db, user, plan, period_months)
    except PaymentError as exc:
        raise ValueError(str(exc))
    return confirmation_url, payment.id


async def _handle_success(db: AsyncSession, payload: dict) -> None:
    # Подпись Token уже проверена фабрикой; здесь — идемпотентная активация подписки.
    await handle_webhook(db, payload)


router = make_payments_router(
    get_db=get_db,
    get_current_user=get_current_user,
    create_payment=_create_payment,
    handle_success=_handle_success,
    route_prefix="/api/payments",
)


@router.get("", response_model=list[PaymentOut])
async def history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PaymentOut]:
    result = await db.execute(
        select(Payment).where(Payment.user_id == user.id).order_by(Payment.created_at.desc())
    )
    return [PaymentOut.model_validate(p) for p in result.scalars().all()]
