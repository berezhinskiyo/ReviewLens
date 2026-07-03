from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Все настройки сервиса через переменные окружения (см. .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ReviewLens"

    # База / очередь
    database_url: str = "postgresql+asyncpg://reviewlens:reviewlens@db:5432/reviewlens"
    redis_url: str = "redis://redis:6379/0"

    # LLM-роутер (OpenAI-совместимый). По умолчанию — polza.ai.
    # Пусто в base_url = напрямую OpenAI. Модели параметризуем без передеплоя.
    openai_api_key: str = ""
    openai_base_url: str = "https://polza.ai/api/v1"
    openai_model_extract: str = "google/gemini-2.5-flash-lite"
    openai_model_cluster: str = "google/gemini-2.5-flash-lite"
    openai_model_synth: str = "deepseek/deepseek-v3.2"

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_days: int = 30

    # Регистрация / согласие (152-ФЗ)
    consent_version: str = "2026-06-29"
    bootstrap_admin_email: str = ""

    # ЮKassa
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""

    # Внешние URL (OAuth redirect + ссылка обратно во фронт)
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"

    # CORS
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost",
            "http://127.0.0.1:5173",
        ]
    )

    # Капча (серверный ключ Яндекс SmartCaptcha; пусто = проверка пропускается)
    smartcaptcha_server_key: str = ""

    # OAuth провайдеры
    yandex_client_id: str = ""
    yandex_client_secret: str = ""
    vk_client_id: str = ""
    vk_client_secret: str = ""

    # Отправка email с кодом (SMTP → консоль в dev)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_ssl: bool = False
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@reviewlens.ru"

    env: str = "development"

    # Включённые маркетплейсы (через запятую). Остальные скраперы есть в коде,
    # но отключены до появления надёжного источника (анти-бот/прокси).
    enabled_marketplaces: str = "wb"

    # Лимиты и экономика
    max_reviews_per_analysis: int = 500
    analysis_cost_budget_kopecks: int = 1500

    @property
    def enabled_marketplaces_set(self) -> set[str]:
        return {m.strip() for m in self.enabled_marketplaces.split(",") if m.strip()}

    # Прокси для скраперов (Ozon/Яндекс/Avito часто требуют РФ/резидентные прокси).
    # Формат: http://user:pass@host:port или socks5://host:port. Пусто = без прокси.
    scraper_proxy: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
