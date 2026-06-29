import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import client_ip, get_current_user, persist_refresh_token
from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_password_hash,
    hash_refresh_token,
    verify_password,
)
from app.db.models import (
    EmailVerificationCode,
    OAuthIdentity,
    RefreshToken,
    User,
)
from app.db.session import get_db
from app.schemas.api import (
    EmailCodeRequest,
    EmailCodeVerify,
    RefreshRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserLoginRequest,
    UserMe,
    UserRegisterRequest,
)
from app.services.emailer import send_email_code
from app.services.subscription import (
    analyses_limit,
    analyses_remaining,
    effective_plan,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# --- Вспомогательное ---------------------------------------------------------


def _access_ttl_seconds() -> int:
    return settings.access_token_expire_minutes * 60


async def _issue_tokens(user: User, db: AsyncSession) -> TokenResponse:
    access = create_access_token(str(user.id))
    refresh_plain = await persist_refresh_token(db, user.id)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh_plain,
        expires_in=_access_ttl_seconds(),
    )


def _hash_code(code: str) -> str:
    return hash_refresh_token(code)


def _is_bootstrap_admin(email: str) -> bool:
    admin = settings.bootstrap_admin_email.strip().lower()
    return bool(admin and email.lower() == admin)


async def verify_smartcaptcha(token: str | None, ip: str | None) -> None:
    """Проверка токена Яндекс SmartCaptcha. Активна только при заданном серверном ключе."""
    server_key = settings.smartcaptcha_server_key.strip()
    if not server_key:
        return
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Подтвердите, что вы не робот"
        )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://smartcaptcha.yandexcloud.net/validate",
                data={"secret": server_key, "token": token, "ip": ip or ""},
            )
        ok = resp.status_code == 200 and resp.json().get("status") == "ok"
    except Exception:  # noqa: BLE001 — недоступность капчи не должна ронять регистрацию
        ok = True
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Проверка капчи не пройдена"
        )


def to_me(user: User) -> UserMe:
    return UserMe(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_admin=user.is_admin,
        email_verified=user.email_verified,
        plan=effective_plan(user),
        subscription_until=user.subscription_until,
        analyses_used_this_period=user.analyses_used_this_period,
        analyses_limit=analyses_limit(user),
        analyses_remaining=analyses_remaining(user),
    )


# --- Регистрация по e-mail с кодом -------------------------------------------


@router.post("/register/request-code")
async def request_register_code(
    payload: EmailCodeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await verify_smartcaptcha(payload.captcha_token, client_ip(request))
    email = str(payload.email).lower()

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email уже зарегистрирован"
        )

    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        EmailVerificationCode(
            email=email,
            code_hash=_hash_code(code),
            password_hash=get_password_hash(payload.password),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
    )
    await db.commit()
    send_email_code(email, code)
    return {"ok": True, "message": "Код отправлен на почту"}


@router.post("/register/verify", response_model=TokenResponse)
async def verify_register_code(
    payload: EmailCodeVerify, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    email = str(payload.email).lower()

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email уже зарегистрирован"
        )

    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(EmailVerificationCode)
        .where(
            EmailVerificationCode.email == email,
            EmailVerificationCode.consumed_at.is_(None),
            EmailVerificationCode.expires_at > now,
        )
        .order_by(EmailVerificationCode.created_at.desc())
    )
    row = result.scalars().first()
    if not row or row.code_hash != _hash_code(payload.code.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный или истёкший код"
        )

    user = User(
        email=email,
        password_hash=row.password_hash,
        is_admin=_is_bootstrap_admin(email),
        email_verified=True,
        consent_at=now,
        consent_version=settings.consent_version,
        plan="free",
    )
    row.consumed_at = now
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return await _issue_tokens(user, db)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegisterRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Прямая регистрация без e-mail-кода (для API-клиентов).

    Веб-интерфейс использует поток /register/request-code → /register/verify.
    """
    if not payload.consent_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нужно принять оферту и политику обработки персональных данных.",
        )
    email = str(payload.email).lower()
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Пользователь уже существует."
        )
    now = datetime.now(timezone.utc)
    user = User(
        email=email,
        password_hash=get_password_hash(payload.password),
        is_admin=_is_bootstrap_admin(email),
        email_verified=True,
        consent_at=now,
        consent_version=settings.consent_version,
        plan="free",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return await _issue_tokens(user, db)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLoginRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    email = str(payload.email).lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверные учётные данные"
        )
    if _is_bootstrap_admin(email) and not user.is_admin:
        user.is_admin = True
        await db.commit()
    return await _issue_tokens(user, db)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_session(
    payload: RefreshRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    token_hash = hash_refresh_token(payload.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    row = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    expires = row.expires_at if row else None
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if not row or row.revoked_at or (expires and expires < now):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # Ротация: старый токен отзываем, выдаём новую пару
    row.revoked_at = now
    await db.commit()

    user = await db.get(User, row.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return await _issue_tokens(user, db)


@router.post("/logout")
async def logout(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hash_refresh_token(payload.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    row = result.scalar_one_or_none()
    if row and not row.revoked_at:
        row.revoked_at = datetime.now(timezone.utc)
        await db.commit()
    return {"ok": True}


@router.get("/me", response_model=UserMe)
async def me(user: User = Depends(get_current_user)) -> UserMe:
    return to_me(user)


@router.patch("/me", response_model=UserMe)
async def update_me(
    payload: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserMe:
    if payload.display_name is not None:
        user.display_name = payload.display_name
    await db.commit()
    return to_me(user)


# --- OAuth (Яндекс / VK) -----------------------------------------------------


def _oauth_config(provider: str) -> dict:
    configs = {
        "yandex": {
            "client_id": settings.yandex_client_id,
            "client_secret": settings.yandex_client_secret,
            "auth_url": "https://oauth.yandex.ru/authorize",
            "token_url": "https://oauth.yandex.ru/token",
            "userinfo_url": "https://login.yandex.ru/info?format=json",
            "scope": "login:email",
        },
        "vk": {
            "client_id": settings.vk_client_id,
            "client_secret": settings.vk_client_secret,
            "auth_url": "https://id.vk.com/authorize",
            "token_url": "https://id.vk.com/oauth2/auth",
            "userinfo_url": "https://id.vk.com/oauth2/user_info",
            "scope": "email",
        },
    }
    if provider not in configs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown provider"
        )
    cfg = configs[provider]
    if not cfg["client_id"] or not cfg["client_secret"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{provider} OAuth is not configured",
        )
    return cfg


def _oauth_redirect_uri(provider: str) -> str:
    return f"{settings.backend_url.rstrip('/')}/api/auth/oauth/{provider}/callback"


def _frontend_url(path: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}{path}"


@router.get("/oauth/{provider}/start")
async def oauth_start(provider: str):
    cfg = _oauth_config(provider)
    state = secrets.token_urlsafe(18)
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": _oauth_redirect_uri(provider),
        "response_type": "code",
        "scope": cfg["scope"],
        "state": state,
    }
    return RedirectResponse(f"{cfg['auth_url']}?{urlencode(params)}")


async def _get_or_create_oauth_user(
    db: AsyncSession,
    provider: str,
    provider_user_id: str,
    email: str,
    display_name: str | None,
) -> User:
    result = await db.execute(
        select(OAuthIdentity).where(
            OAuthIdentity.provider == provider,
            OAuthIdentity.provider_user_id == provider_user_id,
        )
    )
    identity = result.scalar_one_or_none()
    if identity:
        user = await db.get(User, identity.user_id)
        if user:
            if display_name and not user.display_name:
                user.display_name = display_name
                await db.commit()
                await db.refresh(user)
            return user

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if not user:
        user = User(
            email=email,
            password_hash=get_password_hash(secrets.token_urlsafe(24)[:32]),
            email_verified=True,
            display_name=display_name,
            is_admin=_is_bootstrap_admin(email),
            consent_at=now,
            consent_version=settings.consent_version,
            plan="free",
        )
        db.add(user)
        await db.flush()
    else:
        if not user.email_verified:
            user.email_verified = True
        if display_name and not user.display_name:
            user.display_name = display_name

    db.add(
        OAuthIdentity(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            email=email,
        )
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str,
    db: AsyncSession = Depends(get_db),
    state: str | None = None,
):
    cfg = _oauth_config(provider)
    token_payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "redirect_uri": _oauth_redirect_uri(provider),
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(cfg["token_url"], data=token_payload)
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth token exchange failed",
            )
        info_resp = await client.get(
            cfg["userinfo_url"], headers={"Authorization": f"Bearer {access_token}"}
        )
        info_resp.raise_for_status()
        info = info_resp.json()

    provider_user_id = str(info.get("id") or info.get("sub") or "")
    email = info.get("default_email") or info.get("email")
    display_name = (
        info.get("real_name")
        or info.get("display_name")
        or " ".join(filter(None, [info.get("first_name"), info.get("last_name")])).strip()
        or None
    )
    if not provider_user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth user profile has no email",
        )

    user = await _get_or_create_oauth_user(
        db, provider, provider_user_id, str(email).lower(), display_name
    )
    tokens = await _issue_tokens(user, db)
    params = urlencode(
        {"access_token": tokens.access_token, "refresh_token": tokens.refresh_token or ""}
    )
    return RedirectResponse(_frontend_url(f"/auth/oauth/callback?{params}"))
