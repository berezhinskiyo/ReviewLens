import uuid

from authbilling import make_get_current_user
from authbilling import persist_refresh_token as _persist_refresh_token
from authbilling.ratelimit import client_ip  # noqa: F401 — реэкспорт для роутеров
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RefreshToken, User
from app.db.session import get_db


async def persist_refresh_token(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Создаёт refresh-токен, сохраняет его хеш и возвращает «сырое» значение."""
    return await _persist_refresh_token(db, RefreshToken, user_id)


# Пользователь из Bearer-токена. ReviewLens использует UUID-идентификаторы.
get_current_user = make_get_current_user(User, get_db, id_cast=uuid.UUID)
