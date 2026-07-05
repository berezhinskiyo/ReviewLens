"""Интеграция с эквайрингом Т-Банк. Реализация вынесена в общий пакет auth-billing-core.

Тонкий реэкспорт для обратной совместимости импортов проекта.
"""
from authbilling.tinkoff import (  # noqa: F401
    SUCCESS_STATUSES,
    build_receipt,
    gen_token,
    init_payment,
    is_configured,
    terminal_key,
    verify_notification,
)
