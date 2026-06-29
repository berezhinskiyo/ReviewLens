import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    decode_user_id,
    hash_refresh_token,
    new_refresh_token_plain,
)
from app.db.models import RefreshToken, User
from app.db.session import get_db


async def persist_refresh_token(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Создаёт refresh-токен, сохраняет его хеш и возвращает «сырое» значение."""
    plain = new_refresh_token_plain()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days)
    db.add(
        RefreshToken(
            user_id=user_id, token_hash=hash_refresh_token(plain), expires_at=expires_at
        )
    )
    await db.commit()
    return plain


def client_ip(request: Request) -> str:
    """Реальный IP клиента за прокси (X-Forwarded-For / X-Real-IP)."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.headers.get("x-real-ip") or (
        request.client.host if request.client else "unknown"
    )


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется авторизация."
        )
    token = authorization.split(" ", 1)[1]
    user_id = decode_user_id(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Невалидный токен."
        )
    try:
        user = await db.get(User, uuid.UUID(user_id))
    except ValueError:
        user = None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден."
        )
    return user
