"""OAuth-вход через Яндекс и ВК (VK ID + PKCE).

Модуль отвечает только за протокольную часть: сборку authorize-URL, обмен кода на
токен и получение профиля. Создание пользователя и выдача сессии — в роутере, т.к.
это завязано на модели конкретного проекта.
"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from .config import get_settings


@dataclass
class OAuthProfile:
    provider_user_id: str
    email: str
    display_name: str | None


def _provider_configs() -> dict[str, dict]:
    settings = get_settings()
    return {
        "yandex": {
            "client_id": settings.yandex_client_id,
            "client_secret": settings.yandex_client_secret,
            "auth_url": "https://oauth.yandex.ru/authorize",
            "token_url": "https://oauth.yandex.ru/token",
            "userinfo_url": "https://login.yandex.ru/info?format=json",
            "scope": "login:email login:info",
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


def get_oauth_config(provider: str) -> dict:
    configs = _provider_configs()
    if provider not in configs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Неизвестный провайдер")
    cfg = configs[provider]
    if not cfg["client_id"] or not cfg["client_secret"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{provider} OAuth is not configured",
        )
    return cfg


def oauth_redirect_uri(provider: str, route_prefix: str = "/auth") -> str:
    """URL callback-а. route_prefix — префикс монтирования auth-роутера в приложении
    (напр. "/api/auth" у ReviewLens/cv-tailor, "/auth" у mcko)."""
    base = get_settings().backend_url.rstrip("/")
    return f"{base}{route_prefix.rstrip('/')}/oauth/{provider}/callback"


# ── PKCE-хранилище для VK (verifier между /start и /callback) ────────────────
def _vk_pkce_store_path(state: str) -> str:
    safe = "".join(c for c in state if c.isalnum() or c in "-_")
    return f"/tmp/vk_pkce_{safe}.txt"


def build_authorize_url(provider: str, route_prefix: str = "/auth") -> str:
    """Собирает authorize-URL. Для VK генерирует и сохраняет PKCE code_verifier."""
    cfg = get_oauth_config(provider)
    state = secrets.token_urlsafe(18)
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": oauth_redirect_uri(provider, route_prefix),
        "response_type": "code",
        "scope": cfg["scope"],
        "state": state,
    }
    if provider == "vk":
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("ascii")).digest())
            .rstrip(b"=")
            .decode("ascii")
        )
        with open(_vk_pkce_store_path(state), "w") as f:
            f.write(code_verifier)
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"
    return f"{cfg['auth_url']}?{urlencode(params)}"


async def fetch_profile(
    provider: str,
    code: str,
    state: str | None = None,
    device_id: str | None = None,
    route_prefix: str = "/auth",
) -> OAuthProfile:
    """Обменивает authorization code на токен и возвращает профиль пользователя."""
    cfg = get_oauth_config(provider)
    if provider == "vk":
        if not state or not device_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="VK: отсутствует state/device_id"
            )
        try:
            with open(_vk_pkce_store_path(state)) as f:
                code_verifier = f.read().strip()
            os.remove(_vk_pkce_store_path(state))
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Срок действия запроса VK истёк"
            )
        token_payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": cfg["client_id"],
            "device_id": device_id,
            "redirect_uri": oauth_redirect_uri(provider, route_prefix),
            "code_verifier": code_verifier,
        }
    else:
        token_payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "redirect_uri": oauth_redirect_uri(provider, route_prefix),
        }

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(cfg["token_url"], data=token_payload)
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось получить токен авторизации",
            )
        if provider == "vk":
            info_resp = await client.post(
                cfg["userinfo_url"],
                data={"client_id": cfg["client_id"], "access_token": access_token},
            )
        else:
            info_resp = await client.get(
                cfg["userinfo_url"], headers={"Authorization": f"Bearer {access_token}"}
            )
        info_resp.raise_for_status()
        info = info_resp.json()

    if provider == "vk":
        user_data = info.get("user") or {}
        provider_user_id = str(user_data.get("user_id") or "")
        email = user_data.get("email") or token_data.get("email") or f"vk-{provider_user_id}@oauth.local"
        first = (user_data.get("first_name") or "").strip()
        last = (user_data.get("last_name") or "").strip()
        display_name = (f"{first} {last}".strip()) or None
    else:
        provider_user_id = str(info.get("id") or info.get("sub") or info.get("client_id") or "")
        email = info.get("default_email") or info.get("email")
        display_name = (
            info.get("real_name")
            or info.get("display_name")
            or " ".join(filter(None, [info.get("first_name"), info.get("last_name")])).strip()
            or None
        )

    if not provider_user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="В профиле провайдера нет email"
        )
    return OAuthProfile(provider_user_id=provider_user_id, email=str(email).lower(), display_name=display_name)
