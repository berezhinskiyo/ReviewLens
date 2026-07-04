"""Оплата подписки через Т-Банк (T-Bank / Тинькофф Касса)."""

import uuid
from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.core.plans import PURCHASABLE, get_plan
from app.db.models import Payment, User
from app.services import tinkoff


class PaymentError(Exception):
    pass


async def create_payment(
    db: AsyncSession, user: User, plan_code: str, period_months: int
) -> tuple[Payment, str]:
    """Создаёт запись payments(pending) и платёж в Т-Банке, возвращает ссылку на оплату."""
    if plan_code not in PURCHASABLE:
        raise PaymentError(f"Недоступный для покупки тариф: {plan_code}")
    if not tinkoff.is_configured():
        raise PaymentError("Оплата временно недоступна")

    plan = get_plan(plan_code)
    amount_kopecks = plan.price_kopecks * period_months
    amount_rub = amount_kopecks // 100
    if amount_rub <= 0:
        raise PaymentError("Этот тариф нельзя оплатить")

    payment = Payment(
        user_id=user.id,
        amount_kopecks=amount_kopecks,
        plan=plan_code,
        period_months=period_months,
        status="pending",
    )
    db.add(payment)
    await db.flush()

    base = settings.backend_url.rstrip("/")
    front = settings.frontend_url.rstrip("/")
    order_id = str(payment.id)
    try:
        result = await tinkoff.init_payment(
            amount_rub=amount_rub,
            order_id=order_id,
            description=f"Подписка «{plan.title}» — ReviewLens",
            success_url=f"{front}/billing?paid=1",
            fail_url=f"{front}/billing?failed=1",
            notification_url=f"{base}/api/payments/webhook",
            data={
                "payment_id": str(payment.id),
                "user_id": str(user.id),
                "plan_code": plan_code,
            },
            receipt=tinkoff.build_receipt(
                email=user.email,
                item_name=f"Подписка «{plan.title}» — доступ к ReviewLens",
                amount_rub=amount_rub,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        raise PaymentError(f"Не удалось создать платёж: {exc}") from exc

    payment_url = result.get("PaymentURL")
    if not payment_url:
        raise PaymentError("Провайдер не вернул ссылку на оплату")

    payment.yookassa_payment_id = str(result.get("PaymentId") or "")
    await db.commit()
    return payment, payment_url


async def handle_webhook(db: AsyncSession, payload: dict) -> bool:
    """Уведомление Т-Банка: проверяем Token, при успехе активируем подписку.

    Возвращает True, если подпись валидна (эндпоинт всё равно отвечает OK).
    """
    if not tinkoff.verify_notification(payload):
        logger.warning("tinkoff.webhook.bad_token")
        return False

    status_value = str(payload.get("Status", ""))
    if not payload.get("Success") or status_value not in tinkoff.SUCCESS_STATUSES:
        return True  # промежуточный статус — просто подтверждаем приём

    data = payload.get("DATA") or {}
    payment_id = data.get("payment_id") or payload.get("OrderId")
    if not payment_id:
        logger.warning("tinkoff.webhook.no_payment_id")
        return True

    try:
        payment = await db.get(Payment, uuid.UUID(str(payment_id)))
    except (ValueError, TypeError):
        payment = None
    if payment is None:
        logger.warning("tinkoff.webhook.payment_not_found", payment_id=str(payment_id))
        return True

    if payment.status == "succeeded":
        return True  # идемпотентность (AUTHORIZED + CONFIRMED)

    payment.yookassa_payment_id = str(payload.get("PaymentId") or payment.yookassa_payment_id)
    await _apply_successful_payment(db, payment)
    await db.commit()
    return True


async def _apply_successful_payment(db: AsyncSession, payment: Payment) -> None:
    payment.status = "succeeded"
    payment.completed_at = datetime.now(timezone.utc)

    user = await db.get(User, payment.user_id)
    if user is None:
        return

    now = datetime.now(timezone.utc)
    base = (
        user.subscription_until
        if user.subscription_until and user.subscription_until > now
        else now
    )
    user.plan = payment.plan
    user.subscription_until = base + relativedelta(months=payment.period_months)
    user.analyses_used_this_period = 0  # новый период — обнуляем счётчик

    logger.info(
        "subscription.activated",
        user_id=str(user.id),
        plan=user.plan,
        until=user.subscription_until.isoformat(),
    )
