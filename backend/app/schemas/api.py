"""Схемы запросов/ответов API."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Auth --------------------------------------------------------------------


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=900, description="Access token TTL, seconds")


class EmailCodeRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    captcha_token: str | None = None


class EmailCodeVerify(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=12)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=72)


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    consent_accepted: bool = True


class RefreshRequest(BaseModel):
    refresh_token: str


# --- Users -------------------------------------------------------------------


class UserMe(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str | None
    is_admin: bool
    email_verified: bool
    plan: str
    subscription_until: datetime | None
    analyses_used_this_period: int
    analyses_limit: int | None  # None == безлимит
    analyses_remaining: int | None


class UpdateProfileRequest(BaseModel):
    display_name: str | None = None


# --- Analyses ----------------------------------------------------------------


class CreateAnalysisRequest(BaseModel):
    url: str


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    input_url: str
    status: str
    error_message: str | None
    reviews_analyzed_count: int | None
    result: dict[str, Any] | None
    created_at: datetime
    completed_at: datetime | None


class AnalysisListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    input_url: str
    status: str
    reviews_analyzed_count: int | None
    created_at: datetime
    completed_at: datetime | None


# --- Payments ----------------------------------------------------------------


class CreatePaymentRequest(BaseModel):
    plan: str  # starter / pro
    period_months: int = 1


class CreatePaymentResponse(BaseModel):
    confirmation_url: str
    payment_id: uuid.UUID


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount_kopecks: int
    plan: str
    period_months: int
    status: str
    created_at: datetime
    completed_at: datetime | None
