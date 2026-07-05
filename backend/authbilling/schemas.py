"""Общие Pydantic-схемы auth. Доменные схемы (профиль, подписка) остаются в проектах."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int


class UserRegister(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class EmailCodeRequest(BaseModel):
    email: EmailStr
    password: str
    captcha_token: str | None = None


class EmailCodeVerify(BaseModel):
    email: EmailStr
    code: str


class RefreshRequest(BaseModel):
    refresh_token: str
