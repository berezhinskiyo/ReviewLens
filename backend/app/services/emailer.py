"""Отправка email. Реализация вынесена в общий пакет auth-billing-core (async).

Тонкий реэкспорт для обратной совместимости импортов проекта. Тема письма и
транспорт (Postbox/SMTP/консоль) конфигурируются через настройки.
"""
from authbilling.emailer import send_email, send_email_code  # noqa: F401
