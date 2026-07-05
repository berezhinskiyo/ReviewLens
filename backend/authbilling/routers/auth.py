"""Фабрика auth-роутера: единый flow регистрации/входа/OAuth для всех проектов.

Роутер параметризуется моделями и зависимостями конкретного проекта, поэтому не тянет
за собой ни доменные модели, ни доменные схемы. Ответ /me формирует переданный
`me_response(user)`.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import oauth
from ..captcha import verify_smartcaptcha
from ..config import get_settings
from ..models import get_or_create_oauth_user, persist_refresh_token
from ..ratelimit import client_ip
from ..schemas import (
    EmailCodeRequest,
    EmailCodeVerify,
    RefreshRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
)
from ..security import (
    create_access_token,
    get_password_hash,
    hash_refresh_token,
    verify_password,
)


def make_auth_router(
    *,
    user_model: type,
    refresh_model: type,
    email_code_model: type,
    oauth_model: type,
    get_db: Callable[..., Any],
    get_current_user: Callable[..., Any],
    send_email_code: Callable[[str, str], Any],
    me_response: Callable[[Any], Any],
    route_prefix: str = "/auth",
    frontend_callback_path: str = "/auth/oauth/callback",
    consent_version: str | None = None,
    include_me: bool = True,
    include_register: bool = True,
    route_dependencies: dict[str, list] | None = None,
    tags: list[str] | None = None,
) -> APIRouter:
    """Собирает готовый APIRouter аутентификации.

    - route_prefix: префикс монтирования (совпадает с redirect_uri OAuth).
    - send_email_code: async-функция отправки кода (обычно authbilling.emailer.send_email_code).
    - me_response: строит тело ответа /me из объекта пользователя проекта.
    - include_me: добавлять ли GET /me (проект может определить свой /me с доменной схемой).
    - route_dependencies: доп. зависимости на роут (ключи: request_code, verify, register,
      login, refresh, logout) — например rate-limit.
    """
    router = APIRouter(prefix=route_prefix, tags=tags or ["auth"])
    rdeps = route_dependencies or {}

    def _consent_version() -> str:
        return consent_version or get_settings().consent_version

    def _access_ttl_seconds() -> int:
        return get_settings().access_token_expire_minutes * 60

    def _bootstrap_admin() -> str:
        return get_settings().bootstrap_admin_email.strip().lower()

    async def _issue_tokens(user: Any, db: AsyncSession) -> TokenResponse:
        access = create_access_token(str(user.id))
        refresh_plain = await persist_refresh_token(db, refresh_model, user.id)
        return TokenResponse(
            access_token=access, refresh_token=refresh_plain, expires_in=_access_ttl_seconds()
        )

    def _hash_code(code: str) -> str:
        return hash_refresh_token(code)

    def _frontend_url(path: str) -> str:
        base = get_settings().frontend_url.rstrip("/")
        return f"{base}{path}"

    async def _user_by_email(db: AsyncSession, email: str) -> Any:
        return (
            await db.execute(select(user_model).where(user_model.email == email))
        ).scalar_one_or_none()

    # ── Регистрация по email + код подтверждения ─────────────────────────────
    @router.post("/register/request-code", dependencies=rdeps.get("request_code", []))
    async def request_register_code(
        payload: EmailCodeRequest,
        request: Request,
        db: AsyncSession = Depends(get_db),
    ):
        await verify_smartcaptcha(payload.captcha_token, client_ip(request))
        email = str(payload.email).lower()
        if await _user_by_email(db, email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Этот email уже зарегистрирован"
            )
        code = f"{secrets.randbelow(1_000_000):06d}"
        db.add(
            email_code_model(
                email=email,
                code_hash=_hash_code(code),
                password_hash=get_password_hash(payload.password),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            )
        )
        await db.commit()
        await send_email_code(email, code)
        return {"ok": True, "message": "Код отправлен на почту"}

    @router.post(
        "/register/verify", response_model=TokenResponse, dependencies=rdeps.get("verify", [])
    )
    async def verify_register_code(payload: EmailCodeVerify, db: AsyncSession = Depends(get_db)):
        email = str(payload.email).lower()
        if await _user_by_email(db, email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Этот email уже зарегистрирован"
            )
        now = datetime.now(timezone.utc)
        row = (
            await db.execute(
                select(email_code_model)
                .where(
                    email_code_model.email == email,
                    email_code_model.consumed_at.is_(None),
                    email_code_model.expires_at > now,
                )
                .order_by(email_code_model.created_at.desc())
            )
        ).scalars().first()
        if not row or row.code_hash != _hash_code(payload.code.strip()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный или истёкший код"
            )
        user = user_model(
            email=email,
            password_hash=row.password_hash,
            is_admin=bool(_bootstrap_admin() and email == _bootstrap_admin()),
            email_verified=True,
            consent_at=now,
            consent_version=_consent_version(),
        )
        row.consumed_at = now
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return await _issue_tokens(user, db)

    if include_register:

        @router.post("/register", dependencies=rdeps.get("register", []))
        async def register(payload: UserRegister, request: Request, db: AsyncSession = Depends(get_db)):
            await request_register_code(
                EmailCodeRequest(email=payload.email, password=payload.password), request, db
            )
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED, detail="Требуется подтверждение email"
            )

    # ── Вход по email/паролю ─────────────────────────────────────────────────
    @router.post("/login", response_model=TokenResponse, dependencies=rdeps.get("login", []))
    async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
        user = await _user_by_email(db, str(payload.email).lower())
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль"
            )
        if _bootstrap_admin() and user.email.lower() == _bootstrap_admin() and not user.is_admin:
            user.is_admin = True
            await db.commit()
        return await _issue_tokens(user, db)

    @router.post("/refresh", response_model=TokenResponse, dependencies=rdeps.get("refresh", []))
    async def refresh_session(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
        token_hash = hash_refresh_token(payload.refresh_token)
        row = (
            await db.execute(select(refresh_model).where(refresh_model.token_hash == token_hash))
        ).scalar_one_or_none()
        now = datetime.now(timezone.utc)
        expires_at = row.expires_at if row else None
        # SQLite возвращает naive datetime — трактуем как UTC (в Postgres уже aware).
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if not row or row.revoked_at or expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен сессии"
            )
        row.revoked_at = now
        await db.commit()
        user = (
            await db.execute(select(user_model).where(user_model.id == row.user_id))
        ).scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден"
            )
        return await _issue_tokens(user, db)

    @router.post("/logout", dependencies=rdeps.get("logout", []))
    async def logout(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
        token_hash = hash_refresh_token(payload.refresh_token)
        row = (
            await db.execute(select(refresh_model).where(refresh_model.token_hash == token_hash))
        ).scalar_one_or_none()
        if row and not row.revoked_at:
            row.revoked_at = datetime.now(timezone.utc)
            await db.commit()
        return {"ok": True}

    # ── OAuth (Яндекс / ВК) ──────────────────────────────────────────────────
    @router.get("/oauth/{provider}/start")
    async def oauth_start(provider: str):
        return RedirectResponse(oauth.build_authorize_url(provider, route_prefix))

    @router.get("/oauth/{provider}/callback")
    async def oauth_callback(
        provider: str,
        code: str,
        state: str | None = None,
        device_id: str | None = None,
        db: AsyncSession = Depends(get_db),
    ):
        profile = await oauth.fetch_profile(
            provider, code, state=state, device_id=device_id, route_prefix=route_prefix
        )
        user = await get_or_create_oauth_user(
            db,
            user_model=user_model,
            oauth_model=oauth_model,
            provider=provider,
            provider_user_id=profile.provider_user_id,
            email=profile.email,
            display_name=profile.display_name,
            consent_version=_consent_version(),
        )
        tokens = await _issue_tokens(user, db)
        params = urlencode(
            {"access_token": tokens.access_token, "refresh_token": tokens.refresh_token or ""}
        )
        return RedirectResponse(_frontend_url(f"{frontend_callback_path}?{params}"))

    # ── Текущий пользователь ─────────────────────────────────────────────────
    if include_me:

        @router.get("/me")
        async def auth_me(user: Any = Depends(get_current_user)):
            return me_response(user)

    return router
