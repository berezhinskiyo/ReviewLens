"""Generic async-хелперы для работы с моделями auth.

Пакет НЕ навязывает свои SQLAlchemy-модели: у проектов разные типы первичных ключей
(UUID у ReviewLens, Integer у mcko/cv-tailor) и разный набор доменных колонок. Поэтому
классы моделей (`User`, `RefreshToken`, `OAuthIdentity`) передаются параметрами. От моделей
требуются лишь общие колонки: у User — id, email, password_hash, display_name, email_verified,
consent_at, consent_version; у RefreshToken — user_id, token_hash, expires_at, revoked_at;
у OAuthIdentity — user_id, provider, provider_user_id, email.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .security import get_password_hash, hash_refresh_token, new_refresh_token_plain


async def persist_refresh_token(db: AsyncSession, refresh_model: type, user_id: Any) -> str:
    """Создаёт refresh-токен, сохраняет его sha256-хеш и возвращает «сырое» значение."""
    plain = new_refresh_token_plain()
    expires_at = datetime.now(timezone.utc) + timedelta(days=get_settings().refresh_token_days)
    db.add(refresh_model(user_id=user_id, token_hash=hash_refresh_token(plain), expires_at=expires_at))
    await db.commit()
    return plain


async def get_or_create_oauth_user(
    db: AsyncSession,
    *,
    user_model: type,
    oauth_model: type,
    provider: str,
    provider_user_id: str,
    email: str,
    display_name: str | None = None,
    consent_version: str | None = None,
) -> Any:
    """Находит/создаёт пользователя по OAuth-идентичности провайдера.

    Вход через провайдера трактуется как акцепт оферты и согласие на обработку ПДн
    (152-ФЗ): при создании пользователя проставляются consent_at / consent_version.
    """
    consent_version = consent_version or get_settings().consent_version

    identity = (
        await db.execute(
            select(oauth_model).where(
                oauth_model.provider == provider,
                oauth_model.provider_user_id == provider_user_id,
            )
        )
    ).scalar_one_or_none()
    if identity is not None:
        user = (
            await db.execute(select(user_model).where(user_model.id == identity.user_id))
        ).scalar_one_or_none()
        if user is not None:
            if display_name and not user.display_name:
                user.display_name = display_name
                await db.commit()
            return user

    user = (
        await db.execute(select(user_model).where(user_model.email == email))
    ).scalar_one_or_none()
    if user is None:
        user = user_model(
            email=email,
            password_hash=get_password_hash(secrets.token_urlsafe(24)[:32]),
            email_verified=True,
            display_name=display_name,
            consent_at=datetime.now(timezone.utc),
            consent_version=consent_version,
        )
        db.add(user)
        await db.flush()
    else:
        if not user.email_verified:
            user.email_verified = True
        if display_name and not user.display_name:
            user.display_name = display_name

    db.add(
        oauth_model(user_id=user.id, provider=provider, provider_user_id=provider_user_id, email=email)
    )
    await db.commit()
    return user
