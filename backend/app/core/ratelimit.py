"""Rate-limit на Redis. Реализация вынесена в общий пакет auth-billing-core.

Тонкий реэкспорт для обратной совместимости импортов проекта.
"""
from authbilling.ratelimit import client_ip, rate_limit  # noqa: F401
