"""Standalone FastAPI-приложение auth-billing-core (форма «как сервис»).

Запуск: `uvicorn authbilling.service.app:app`. Хранилище — SQLite (async) по умолчанию,
переопределяется переменной `AB_DATABASE_URL`. Это заготовка под централизованный SSO;
проекты-библиотеки его не используют.
"""
from __future__ import annotations

import os

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .. import configure, get_settings
from ..deps import make_get_current_user
from ..emailer import send_email_code
from ..routers import make_auth_router
from .models import Base, EmailVerificationCode, OAuthIdentity, RefreshToken, User

configure(get_settings())

_engine = create_async_engine(os.getenv("AB_DATABASE_URL", "sqlite+aiosqlite:///./authbilling.db"))
_Session = async_sessionmaker(_engine, expire_on_commit=False)


async def get_db():
    async with _Session() as session:
        yield session


get_current_user = make_get_current_user(User, get_db, id_cast=int)


def _me(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "is_admin": bool(user.is_admin),
    }


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="auth-billing-core", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    make_auth_router(
        user_model=User,
        refresh_model=RefreshToken,
        email_code_model=EmailVerificationCode,
        oauth_model=OAuthIdentity,
        get_db=get_db,
        get_current_user=get_current_user,
        send_email_code=send_email_code,
        me_response=_me,
        route_prefix="/auth",
    )
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
