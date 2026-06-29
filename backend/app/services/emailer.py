"""Отправка email с кодом подтверждения. SMTP при наличии настроек, иначе консоль."""

import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.core.logging import logger


def send_email_code(to_email: str, code: str) -> None:
    subject = "Код подтверждения ReviewLens"
    body = (
        f"Ваш код подтверждения: {code}\n\n"
        "Код действует 15 минут. Если вы не регистрировались — игнорируйте письмо."
    )

    if not settings.smtp_host:
        # dev: печатаем код в логи
        logger.info("email.code.console", to=to_email, code=code)
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg.set_content(body)

    try:
        if settings.smtp_ssl:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
            server.starttls()
        with server:
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        logger.info("email.code.sent", to=to_email)
    except Exception as exc:  # noqa: BLE001 — сбой почты не должен ронять регистрацию
        logger.error("email.code.failed", to=to_email, error=str(exc))
