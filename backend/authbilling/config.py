"""Общие настройки auth + billing.

`AuthBillingSettings` содержит переменные окружения, общие для всех проектов.
Каждый проект наследует свой `Settings(AuthBillingSettings)` и добавляет доменные
поля. Имена полей совпадают с уже существующими в проектах, чтобы миграция была
бесшовной.

Пакет получает конкретный объект настроек через `authbilling.configure(settings)`.
Если `configure` не вызван (например, при запуске пакета отдельным сервисом),
настройки читаются напрямую из окружения через `AuthBillingSettings()`.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthBillingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "auth-billing"

    # ── JWT / сессии ─────────────────────────────────────────────────────────
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_days: int = 30

    # ── Регистрация / согласие (152-ФЗ) ─────────────────────────────────────
    consent_version: str = "2026-06-29"
    bootstrap_admin_email: str = ""

    # ── Внешние URL (OAuth redirect + возврат во фронт) ─────────────────────
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"

    # ── Капча (серверный ключ Яндекс SmartCaptcha; пусто = проверка пропускается)
    smartcaptcha_server_key: str = ""

    # ── OAuth-провайдеры ─────────────────────────────────────────────────────
    yandex_client_id: str = ""
    yandex_client_secret: str = ""
    vk_client_id: str = ""
    vk_client_secret: str = ""

    # ── Отправка email с кодом. Приоритет: Postbox HTTP → SMTP → консоль (dev)
    email_http_endpoint: str = ""  # напр. https://postbox.cloud.yandex.net
    email_http_key_id: str = ""    # access key id статического ключа сервисного аккаунта
    email_http_secret: str = ""    # secret этого ключа
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_ssl: bool = False
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@example.com"
    email_subject: str = "Код подтверждения"

    # ── Эквайринг Т-Банк (T-Bank / Тинькофф Касса) ───────────────────────────
    tinkoff_terminal_key: str = ""
    tinkoff_password: str = ""
    tinkoff_api_url: str = "https://securepay.tinkoff.ru/v2/"
    tinkoff_taxation: str = "usn_income"
    tinkoff_vat: str = "none"

    # ── Rate-limit ───────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost",
            "http://127.0.0.1:5173",
        ]
    )


# Активная конфигурация пакета. Заполняется через configure().
_settings: AuthBillingSettings | None = None


@lru_cache
def _settings_from_env() -> AuthBillingSettings:
    return AuthBillingSettings()


def configure(settings: AuthBillingSettings) -> None:
    """Регистрирует объект настроек проекта для использования внутри пакета."""
    global _settings
    _settings = settings


def get_settings() -> AuthBillingSettings:
    """Текущие настройки: заданные через configure() либо прочитанные из окружения."""
    return _settings if _settings is not None else _settings_from_env()
