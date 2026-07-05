"""Аутентификация ReviewLens поверх общего пакета auth-billing-core.

Регистрация/вход/refresh/OAuth (Яндекс, ВК)/logout собираются фабрикой
`make_auth_router`. Доменная часть — тело ответа /me (тариф и лимиты анализов)
и PATCH /me — определяются здесь.
"""
from authbilling import make_auth_router
from authbilling.emailer import send_email_code
from authbilling.ratelimit import rate_limit
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import EmailVerificationCode, OAuthIdentity, RefreshToken, User
from app.db.session import get_db
from app.schemas.api import UpdateProfileRequest, UserMe
from app.services.subscription import analyses_limit, analyses_remaining, effective_plan


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


router = make_auth_router(
    user_model=User,
    refresh_model=RefreshToken,
    email_code_model=EmailVerificationCode,
    oauth_model=OAuthIdentity,
    get_db=get_db,
    get_current_user=get_current_user,
    send_email_code=send_email_code,
    me_response=to_me,
    route_prefix="/api/auth",
    frontend_callback_path="/auth/oauth/callback",
    route_dependencies={
        "request_code": [Depends(rate_limit("register_code", limit=5, window_seconds=300))],
        "verify": [Depends(rate_limit("register_verify", limit=15, window_seconds=300))],
        "login": [Depends(rate_limit("login", limit=10, window_seconds=300))],
    },
)


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
