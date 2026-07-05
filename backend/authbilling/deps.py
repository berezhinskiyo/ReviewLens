"""Фабрики FastAPI-зависимостей аутентификации.

`make_get_current_user` строит зависимость, извлекающую пользователя из Bearer-токена,
параметризуясь классом модели `User` и зависимостью сессии `get_db` конкретного проекта.
"""
from __future__ import annotations

from typing import Any, Callable

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .ratelimit import client_ip  # реэкспорт для удобства проектов
from .security import decode_user_id

__all__ = ["client_ip", "make_get_current_user"]


def make_get_current_user(
    user_model: type,
    get_db: Callable[..., Any],
    *,
    id_cast: Callable[[str], Any] = str,
    check_deleted: bool = True,
):
    """Возвращает async-зависимость get_current_user.

    id_cast — преобразование sub-строки в тип первичного ключа (uuid.UUID для ReviewLens,
    int для mcko/cv-tailor). check_deleted — отклонять пользователей с deleted_at.
    """

    async def get_current_user(
        authorization: str | None = Header(default=None),
        db: AsyncSession = Depends(get_db),
    ):
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
            key = id_cast(user_id)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Невалидный токен."
            )
        user = (
            await db.execute(select(user_model).where(user_model.id == key))
        ).scalar_one_or_none()
        if user is None or (check_deleted and getattr(user, "deleted_at", None) is not None):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден."
            )
        return user

    return get_current_user
