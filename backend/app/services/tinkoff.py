"""Интеграция с эквайрингом Т-Банк (T-Bank / Тинькофф Касса).

Документация: https://developer.tbank.ru/eacq/
- Init: POST {API}/Init → PaymentURL, PaymentId
- Уведомления (Notification) приходят на NotificationURL, подписаны Token.

Подпись Token: берутся КОРНЕВЫЕ скалярные поля (без вложенных Receipt/DATA и без
самого Token), добавляется пароль терминала (ключ Password), пары сортируются по
ключу, значения конкатенируются, берётся SHA-256 (hex).
"""

import hashlib
import hmac

import httpx

from app.core.config import settings

SUCCESS_STATUSES = {"CONFIRMED", "AUTHORIZED"}


def _api_url() -> str:
    return settings.tinkoff_api_url.strip().rstrip("/") + "/"


def is_configured() -> bool:
    return bool(settings.tinkoff_terminal_key.strip() and settings.tinkoff_password.strip())


def _stringify(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def gen_token(params: dict, password: str | None = None) -> str:
    """SHA-256 подпись по корневым скалярным полям (+ Password)."""
    pwd = password if password is not None else settings.tinkoff_password.strip()
    flat = {
        k: _stringify(v)
        for k, v in params.items()
        if k != "Token" and not isinstance(v, (dict, list))
    }
    flat["Password"] = pwd
    concatenated = "".join(flat[k] for k in sorted(flat))
    return hashlib.sha256(concatenated.encode("utf-8")).hexdigest()


def build_receipt(*, email: str, item_name: str, amount_rub: int) -> dict:
    """Чек 54-ФЗ для одной позиции-услуги."""
    amount_kop = int(amount_rub) * 100
    receipt: dict = {
        "Taxation": settings.tinkoff_taxation.strip(),
        "Items": [
            {
                "Name": item_name[:128],
                "Price": amount_kop,
                "Quantity": 1,
                "Amount": amount_kop,
                "Tax": settings.tinkoff_vat.strip(),
                "PaymentMethod": "full_payment",
                "PaymentObject": "service",
            }
        ],
    }
    if email:
        receipt["Email"] = email
    return receipt


async def init_payment(
    *,
    amount_rub: int,
    order_id: str,
    description: str,
    success_url: str | None = None,
    fail_url: str | None = None,
    notification_url: str | None = None,
    data: dict | None = None,
    receipt: dict | None = None,
) -> dict:
    """Создаёт платёж в Т-Банке, возвращает разобранный JSON ответа Init.

    Бросает RuntimeError, если Init вернул Success=false.
    """
    body: dict = {
        "TerminalKey": settings.tinkoff_terminal_key.strip(),
        "Amount": int(amount_rub) * 100,  # в копейках
        "OrderId": order_id,
        "Description": description[:140],
    }
    if success_url:
        body["SuccessURL"] = success_url
    if fail_url:
        body["FailURL"] = fail_url
    if notification_url:
        body["NotificationURL"] = notification_url
    if data:
        body["DATA"] = {str(k): str(v) for k, v in data.items()}
    if receipt:
        body["Receipt"] = receipt

    body["Token"] = gen_token(body)

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(_api_url() + "Init", json=body)
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("Success"):
        raise RuntimeError(
            f"Tinkoff Init failed: {payload.get('ErrorCode')} "
            f"{payload.get('Message')} {payload.get('Details')}"
        )
    return payload


def verify_notification(payload: dict) -> bool:
    """Проверяет Token входящего уведомления."""
    received = str(payload.get("Token", ""))
    if not received:
        return False
    expected = gen_token(payload)
    return hmac.compare_digest(received, expected)
