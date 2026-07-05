"""Пароли, JWT access-токены и refresh-токены. Чистая логика без сетевого I/O.

Пароли — bcrypt напрямую (passlib не используем из-за несовместимости с bcrypt>=4.1).
bcrypt принимает не более 72 байт — безопасно усекаем.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from .config import get_settings


# ── Пароли ───────────────────────────────────────────────────────────────────
def _to_bcrypt_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:72]


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(_to_bcrypt_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bcrypt_bytes(plain_password), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ── JWT access-токены ─────────────────────────────────────────────────────────
def create_access_token(subject: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire, "typ": "access"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def decode_user_id(token: str) -> str | None:
    """Возвращает user_id (sub) или None при невалидном токене."""
    try:
        payload = decode_access_token(token)
    except JWTError:
        return None
    sub = payload.get("sub")
    return str(sub) if sub else None


# ── Refresh-токены: в БД хранится только sha256-хеш «сырого» значения ─────────
def new_refresh_token_plain() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()
