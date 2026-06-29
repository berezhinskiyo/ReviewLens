"""Создаёт (или повышает до админа) пользователя-администратора.

Запуск:
    python -m app.scripts.create_admin
Переопределить креды можно через переменные окружения:
    ADMIN_EMAIL=... ADMIN_PASSWORD=... python -m app.scripts.create_admin
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


async def main() -> None:
    email = os.getenv("ADMIN_EMAIL", DEFAULT_EMAIL).lower()
    password = os.getenv("ADMIN_PASSWORD", DEFAULT_PASSWORD)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                email=email,
                password_hash=get_password_hash(password),
                display_name="Администратор",
                is_admin=True,
                email_verified=True,
                consent_at=datetime.now(timezone.utc),
                consent_version=settings.consent_version,
                plan="pro",  # админу — безлимит
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"Создан админ {user.id}")
        else:
            # Повышаем существующего пользователя и (при желании) сбрасываем пароль
            user.is_admin = True
            user.email_verified = True
            if os.getenv("ADMIN_PASSWORD"):
                user.password_hash = get_password_hash(password)
            await db.commit()
            print(f"Пользователь повышен до админа {user.id}")

        print(f"\nEmail:    {email}")
        print(f"Пароль:   {password}")
        print(f"is_admin: True")
        print("\nAccess token (Authorization: Bearer ...):\n")
        print(create_access_token(str(user.id)))


if __name__ == "__main__":
    asyncio.run(main())
