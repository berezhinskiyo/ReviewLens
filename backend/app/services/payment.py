"""Интеграция с ЮKassa: создание платежа и обработка вебхука."""

import uuid
from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.core.plans import PURCHASABLE, get_plan
from app.db.models import Payment, User


class PaymentError(Exception):
    pass


def _yookassa_configured() -> bool:
    return bool(settings.yookassa_shop_id and settings.yookassa_secret_key)


async def create_payment(
    db: AsyncSession, user: User, plan_code: str, period_months: int
) -> tuple[Payment, str]:
    """Создаёт запись payments(pending) и платёж в ЮKassa, возвращает confirmation_url."""
    if plan_code not in PURCHASABLE:
        raise PaymentError(f"Недоступный для покупки тариф: {plan_code}")

    plan = get_plan(plan_code)
    amount_kopecks = plan.price_kopecks * period_months

    payment = Payment(
        user_id=user.id,
        amount_kopecks=amount_kopecks,
        plan=plan_code,
        period_months=period_months,
        status="pending",
    )
    db.add(payment)
    await db.flush()

    confirmation_url = await _yookassa_create(
        payment_id=payment.id,
        amount_kopecks=amount_kopecks,
        description=f"ReviewLens — тариф «{plan.title}», {period_months} мес.",
    )

    await db.commit()
    return payment, confirmation_url


async def _yookassa_create(
    payment_id: uuid.UUID, amount_kopecks: int, description: str
) -> str:
    """Вызов ЮKassa API. В dev без ключей возвращаем фейковый URL для прохода сценария."""
    return_url = f"{settings.frontend_url}/billing?payment={payment_id}"

    if not _yookassa_configured():
        logger.warning("yookassa.not_configured", payment_id=str(payment_id))
        return f"{settings.frontend_url}/billing?mock_payment={payment_id}"

    from yookassa import Configuration, Payment as YkPayment  # noqa: N813

    Configuration.account_id = settings.yookassa_shop_id
    Configuration.secret_key = settings.yookassa_secret_key

    yk = YkPayment.create(
        {
            "amount": {"value": f"{amount_kopecks / 100:.2f}", "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": return_url},
            "capture": True,
            "description": description,
            "metadata": {"payment_id": str(payment_id)},
            # Чек 54-ФЗ выбивается автоматически интегрированной онлайн-кассой ЮKassa
            "receipt": {
                "customer": {"email": "noreply@reviewlens.ru"},
                "items": [
                    {
                        "description": description[:128],
                        "quantity": "1.00",
                        "amount": {
                            "value": f"{amount_kopecks / 100:.2f}",
                            "currency": "RUB",
                        },
                        "vat_code": 1,
                        "payment_mode": "full_payment",
                        "payment_subject": "service",
                    }
                ],
            },
        },
        str(payment_id),  # idempotence key
    )

    # Сохраняем yookassa_payment_id отдельным апдейтом (вызывающий код делает commit)
    return yk.confirmation.confirmation_url


async def attach_yookassa_id(db: AsyncSession, payment: Payment, yk_id: str) -> None:
    payment.yookassa_payment_id = yk_id
    await db.flush()


async def handle_webhook(db: AsyncSession, event: dict) -> None:
    """Обработка вебхука ЮKassa: подтверждаем платёж, продлеваем подписку."""
    obj = event.get("object", {})
    yk_id = obj.get("id")
    status = obj.get("status")
    metadata = obj.get("metadata") or {}
    payment_id = metadata.get("payment_id")

    if not payment_id:
        logger.warning("yookassa.webhook.no_payment_id", yk_id=yk_id)
        return

    result = await db.execute(select(Payment).where(Payment.id == uuid.UUID(payment_id)))
    payment = result.scalar_one_or_none()
    if payment is None:
        logger.warning("yookassa.webhook.payment_not_found", payment_id=payment_id)
        return

    if payment.status == "succeeded":
        return  # идемпотентность

    if yk_id and not payment.yookassa_payment_id:
        payment.yookassa_payment_id = yk_id

    if status == "succeeded":
        await _apply_successful_payment(db, payment)
    elif status in ("canceled", "refunded"):
        payment.status = status

    await db.commit()


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
    # Новый период — обнуляем счётчик анализов
    user.analyses_used_this_period = 0

    logger.info(
        "subscription.activated",
        user_id=str(user.id),
        plan=user.plan,
        until=user.subscription_until.isoformat(),
    )
