from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import logger
from app.db.models import Payment, User
from app.db.session import get_db
from app.schemas.api import (
    CreatePaymentRequest,
    CreatePaymentResponse,
    PaymentOut,
)
from app.services.payment import (
    PaymentError,
    create_payment,
    handle_webhook,
)

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("", response_model=CreatePaymentResponse)
async def create(
    payload: CreatePaymentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CreatePaymentResponse:
    try:
        payment, confirmation_url = await create_payment(
            db, user, payload.plan, payload.period_months
        )
    except PaymentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return CreatePaymentResponse(confirmation_url=confirmation_url, payment_id=payment.id)


@router.post("/webhook")
async def webhook(request: Request, db: AsyncSession = Depends(get_db)) -> PlainTextResponse:
    """Уведомление Т-Банка. Без auth — доверие по подписи Token."""
    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bad payload")

    logger.info("tinkoff.webhook.received", status=payload.get("Status"))
    await handle_webhook(db, payload)
    # Т-Банк ждёт тело "OK", иначе будет повторять уведомление
    return PlainTextResponse("OK")


@router.get("", response_model=list[PaymentOut])
async def history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PaymentOut]:
    result = await db.execute(
        select(Payment)
        .where(Payment.user_id == user.id)
        .order_by(Payment.created_at.desc())
    )
    return [PaymentOut.model_validate(p) for p in result.scalars().all()]
