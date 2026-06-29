"""Создаёт тестового пользователя (email+пароль) и печатает access-токен.

Запуск: python -m app.scripts.create_test_user
"""

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.db.models import User
from app.db.session import AsyncSessionLocal

TEST_EMAIL = "test@reviewlens.ru"
TEST_PASSWORD = "test12345"


async def main() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == TEST_EMAIL))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                email=TEST_EMAIL,
                password_hash=get_password_hash(TEST_PASSWORD),
                display_name="Тестовый Селлер",
                email_verified=True,
                consent_at=datetime.now(timezone.utc),
                consent_version=settings.consent_version,
                plan="free",
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"Создан пользователь {user.id} ({TEST_EMAIL} / {TEST_PASSWORD})")
        else:
            print(f"Пользователь уже есть {user.id} ({TEST_EMAIL})")

        token = create_access_token(str(user.id))
        print("\nAccess token (для Authorization: Bearer ...):\n")
        print(token)


if __name__ == "__main__":
    asyncio.run(main())
