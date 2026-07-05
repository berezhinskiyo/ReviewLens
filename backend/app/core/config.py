from functools import lru_cache

from authbilling import AuthBillingSettings, configure
from pydantic import Field


class Settings(AuthBillingSettings):
    """Настройки сервиса. Общие поля auth/billing (JWT, OAuth, SMTP, Т-Банк, капча,
    consent, redis) наследуются из AuthBillingSettings; ниже — доменные для ReviewLens."""

    app_name: str = "ReviewLens"

    # База / очередь
    database_url: str = "postgresql+asyncpg://reviewlens:reviewlens@db:5432/reviewlens"
    redis_url: str = "redis://redis:6379/0"

    # LLM-роутер (OpenAI-совместимый). По умолчанию — polza.ai.
    openai_api_key: str = ""
    openai_base_url: str = "https://polza.ai/api/v1"
    openai_model_extract: str = "google/gemini-2.5-flash-lite"
    openai_model_cluster: str = "google/gemini-2.5-flash-lite"
    openai_model_synth: str = "deepseek/deepseek-v3.2"

    # Согласие 152-ФЗ / письма — переопределяем дефолты под бренд
    consent_version: str = "2026-06-29"
    smtp_from: str = "noreply@reviewlens.ru"
    email_subject: str = "Код подтверждения ReviewLens"

    # ЮKassa (историческое поле, платежи идут через Т-Банк)
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost",
            "http://127.0.0.1:5173",
        ]
    )

    env: str = "development"

    # Включённые маркетплейсы (через запятую)
    enabled_marketplaces: str = "wb"

    # Лимиты и экономика
    max_reviews_per_analysis: int = 500
    analysis_cost_budget_kopecks: int = 1500

    @property
    def enabled_marketplaces_set(self) -> set[str]:
        return {m.strip() for m in self.enabled_marketplaces.split(",") if m.strip()}

    # Прокси для скраперов
    scraper_proxy: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Регистрируем настройки проекта в пакете auth-billing-core (используется его модулями).
configure(settings)
