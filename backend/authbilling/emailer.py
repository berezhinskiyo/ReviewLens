"""Отправка email с кодом подтверждения (async).

Порядок выбора транспорта:
1. HTTP-API Yandex Cloud Postbox (AWS SES v2 SendEmail, подпись SigV4) — если задан
   `email_http_endpoint` (+ `email_http_key_id` / `email_http_secret`).
2. SMTP — если задан `smtp_host` (блокирующий smtplib выносится в отдельный поток).
3. Иначе код печатается в лог (dev-режим), регистрация работает end-to-end.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage

import httpx

from .config import get_settings

logger = logging.getLogger("authbilling.emailer")


def _code_body(code: str) -> str:
    return (
        f"Ваш код подтверждения: {code}\n\n"
        "Код действует 15 минут. Если вы не регистрировались — игнорируйте письмо."
    )


# ── Yandex Postbox (AWS SES v2 SendEmail, SigV4) ─────────────────────────────
def _host(endpoint: str) -> str:
    return endpoint.removeprefix("https://").removeprefix("http://").split("/")[0]


def _sigv4_key(secret: str, date: str, region: str, service: str) -> bytes:
    def sign(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode(), hashlib.sha256).digest()

    return sign(sign(sign(sign(f"AWS4{secret}".encode(), date), region), service), "aws4_request")


async def _send_via_http(to: str, subject: str, text: str) -> None:
    settings = get_settings()
    endpoint = settings.email_http_endpoint.strip().rstrip("/")
    key_id = settings.email_http_key_id.strip()
    secret = settings.email_http_secret.strip()
    from_addr = settings.smtp_from.strip()

    path = "/v2/email/outbound-emails"
    host = _host(endpoint)
    service = "ses"
    region = "ru-central1"
    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")

    payload = json.dumps(
        {
            "FromEmailAddress": from_addr,
            "Destination": {"ToAddresses": [to]},
            "Content": {
                "Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": text, "Charset": "UTF-8"}},
                }
            },
        }
    )

    content_hash = hashlib.sha256(payload.encode()).hexdigest()
    canonical_headers = f"content-type:application/json\nhost:{host}\nx-amz-date:{amz_date}\n"
    signed_headers = "content-type;host;x-amz-date"
    canonical_request = "\n".join(["POST", path, "", canonical_headers, signed_headers, content_hash])

    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        ]
    )

    signing_key = _sigv4_key(secret, date_stamp, region, service)
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    auth_header = (
        f"AWS4-HMAC-SHA256 Credential={key_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            endpoint + path,
            content=payload.encode(),
            headers={
                "Content-Type": "application/json",
                "X-Amz-Date": amz_date,
                "Authorization": auth_header,
            },
        )
    if resp.status_code >= 400:
        logger.error("email.postbox.error status=%s body=%s", resp.status_code, resp.text[:400])
    resp.raise_for_status()


# ── SMTP (блокирующий smtplib выносим в поток) ───────────────────────────────
def _send_via_smtp_blocking(to: str, subject: str, text: str) -> None:
    settings = get_settings()
    host = settings.smtp_host.strip()
    port = settings.smtp_port
    user = settings.smtp_user.strip()
    password = settings.smtp_password.strip()
    from_addr = (settings.smtp_from or user or "noreply@example.com").strip()
    use_ssl = settings.smtp_ssl or port == 465

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)

    if use_ssl:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, timeout=15, context=ctx) as smtp:
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)


# ── Универсальная отправка ────────────────────────────────────────────────────
async def send_email(to: str, subject: str, text: str) -> None:
    settings = get_settings()
    if settings.email_http_endpoint.strip():
        await _send_via_http(to, subject, text)
        logger.info("email.sent channel=postbox to=%s", to)
    elif settings.smtp_host.strip():
        await asyncio.to_thread(_send_via_smtp_blocking, to, subject, text)
        logger.info("email.sent channel=smtp to=%s", to)
    else:
        logger.info("email.code.console to=%s subject=%s body=%s", to, subject, text)


async def send_email_code(to_email: str, code: str) -> None:
    try:
        await send_email(to_email, get_settings().email_subject, _code_body(code))
    except Exception as exc:  # noqa: BLE001 — сбой почты не должен ронять регистрацию
        logger.error("email.code.failed to=%s error=%s", to_email, exc)
