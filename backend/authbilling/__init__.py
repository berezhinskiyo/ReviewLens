"""auth-billing-core — общий пакет аутентификации (email/Яндекс/ВК) и оплаты (Т-Банк).

Быстрый старт (как библиотека):

    from authbilling import configure
    from authbilling.deps import make_get_current_user
    from authbilling.routers import make_auth_router, make_payments_router

    configure(settings)  # settings: AuthBillingSettings или наследник

Пакет также можно поднять отдельным сервисом: `authbilling.service.app:app` (FastAPI).
"""
from __future__ import annotations

from . import captcha, emailer, oauth, ratelimit, security, tinkoff
from .config import AuthBillingSettings, configure, get_settings
from .deps import make_get_current_user
from .models import get_or_create_oauth_user, persist_refresh_token
from .ratelimit import client_ip, rate_limit
from .routers import make_auth_router, make_payments_router

__all__ = [
    "AuthBillingSettings",
    "configure",
    "get_settings",
    "make_get_current_user",
    "make_auth_router",
    "make_payments_router",
    "get_or_create_oauth_user",
    "persist_refresh_token",
    "client_ip",
    "rate_limit",
    "security",
    "oauth",
    "emailer",
    "tinkoff",
    "captcha",
    "ratelimit",
]
