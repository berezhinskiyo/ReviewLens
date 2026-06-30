"""Создаёт (или обновляет) пользователя с безлимитным доступом.

Запуск:
    python -m app.scripts.create_admin
Переопределить через переменные окружения:
    ADMIN_EMAIL=...        e-mail (по умолчанию admin@reviewlens.ru)
    ADMIN_PASSWORD=...     пароль
    ADMIN_IS_ADMIN=0       создать обычного пользователя (не админа), но с безлимитом
"""

import asyncio
import os
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.db.models import User
from app.db.session import AsyncSessionLocal

DEFAULT_EMAIL = "admin@reviewlens.ru"
DEFAULT_PASSWORD = "RL-rlXIHrHufVC32S"

# Безлимит даём через активную pro-подписку с дальним сроком действия.
FAR_FUTURE = datetime(2100, 1, 1, tzinfo=timezone.utc)


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() not in ("0", "false", "no", "")


async def main() -> None:
    email = os.getenv("ADMIN_EMAIL", DEFAULT_EMAIL).lower()
    password = os.getenv("ADMIN_PASSWORD", DEFAULT_PASSWORD)
    is_admin = _env_bool("ADMIN_IS_ADMIN", True)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                email=email,
                password_hash=get_password_hash(password),
                display_name="Администратор" if is_admin else "Тестовый Селлер",
                is_admin=is_admin,
                email_verified=True,
                consent_at=datetime.now(timezone.utc),
                consent_version=settings.consent_version,
                plan="pro",  # безлимит
                subscription_until=FAR_FUTURE,
                analyses_used_this_period=0,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"Создан пользователь {user.id}")
        else:
            user.is_admin = is_admin or user.is_admin
            user.email_verified = True
            user.plan = "pro"
            user.subscription_until = FAR_FUTURE
            user.analyses_used_this_period = 0
            if os.getenv("ADMIN_PASSWORD"):
                user.password_hash = get_password_hash(password)
            await db.commit()
            print(f"Пользователь обновлён {user.id}")

        print(f"\nEmail:    {email}")
        print(f"Пароль:   {password}")
        print(f"is_admin: {is_admin}")
        print("Лимит:    безлимит (план pro до 2100)")
        print("\nAccess token (Authorization: Bearer ...):\n")
        print(create_access_token(str(user.id)))


if __name__ == "__main__":
    asyncio.run(main())
