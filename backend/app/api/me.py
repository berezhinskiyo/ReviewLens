"""Права субъекта ПДн (152-ФЗ, ст. 14): доступ к данным и удаление аккаунта."""

import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import get_password_hash
from app.db.models import (
    Analysis,
    EmailVerificationCode,
    OAuthIdentity,
    Payment,
    RefreshToken,
    User,
)
from app.db.session import get_db

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("/data-export")
async def data_export(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Выгрузка всех данных пользователя в машиночитаемом виде (право на доступ)."""
    analyses = (
        await db.execute(select(Analysis).where(Analysis.user_id == user.id))
    ).scalars().all()
    payments = (
        await db.execute(select(Payment).where(Payment.user_id == user.id))
    ).scalars().all()
    identities = (
        await db.execute(select(OAuthIdentity).where(OAuthIdentity.user_id == user.id))
    ).scalars().all()

    data = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profile": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "email_verified": user.email_verified,
            "plan": user.plan,
            "subscription_until": user.subscription_until.isoformat()
            if user.subscription_until
            else None,
            "consent_at": user.consent_at.isoformat() if user.consent_at else None,
            "consent_version": user.consent_version,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "oauth_identities": [
            {"provider": i.provider, "email": i.email} for i in identities
        ],
        "analyses": [
            {
                "id": str(a.id),
                "input_url": a.input_url,
                "status": a.status,
                "reviews_analyzed_count": a.reviews_analyzed_count,
                "result": a.result,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in analyses
        ],
        "payments": [
            {
                "id": str(p.id),
                "amount_kopecks": p.amount_kopecks,
                "plan": p.plan,
                "period_months": p.period_months,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in payments
        ],
    }
    response.headers["Content-Disposition"] = (
        'attachment; filename="reviewlens-data-export.json"'
    )
    return data


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Удаление аккаунта = отзыв согласия + анонимизация ПДн (152-ФЗ ст. 9, 14).

    Анализы, refresh-токены и OAuth-привязки удаляются. Платежи сохраняются
    обезличенными — данные финансовых операций нужны для налогового учёта.
    Профиль анонимизируется, вход под ним больше невозможен.
    """
    uid = user.id

    # Удаляем персональные данные пользователя
    await db.execute(delete(Analysis).where(Analysis.user_id == uid))
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == uid))
    await db.execute(delete(OAuthIdentity).where(OAuthIdentity.user_id == uid))
    await db.execute(
        delete(EmailVerificationCode).where(EmailVerificationCode.email == user.email)
    )

    # Анонимизируем учётную запись (платежи остаются привязаны к обезличенному id)
    anon_email = f"deleted-{uuid.uuid4().hex}@deleted.local"
    await db.execute(
        update(User)
        .where(User.id == uid)
        .values(
            email=anon_email,
            password_hash=get_password_hash(secrets.token_urlsafe(32)),
            display_name=None,
            email_verified=False,
            is_admin=False,
            deleted_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
