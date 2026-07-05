from app.services import tinkoff


def test_tinkoff_token_matches_docs_example() -> None:
    # Пример из документации Т-Банка (developer.tbank.ru): корневые скалярные
    # поля + Password, сортировка по ключу, конкатенация значений, SHA-256.
    params = {
        "TerminalKey": "MerchantTerminalKey",
        "Amount": 19200,
        "OrderId": "21050",
        "Description": "Подарочная карта на 1000 рублей",
    }
    # Ожидаемое = независимый SHA-256 от конкатенации
    # "19200" + Description + "21050" + Password + "MerchantTerminalKey"
    token = tinkoff.gen_token(params, password="usaf8fw8fsw21g")
    assert token == "c25b8314764b49ed1dfd68c196bb8ad64397de34b5c0e460c216f4b08176c789"


def test_tinkoff_token_ignores_nested_and_token() -> None:
    # Вложенные Receipt/DATA и само поле Token в подписи не участвуют
    base = {"TerminalKey": "T", "Amount": 100, "OrderId": "o1"}
    with_nested = {
        **base,
        "Receipt": {"Items": []},
        "DATA": {"x": "y"},
        "Token": "whatever",
    }
    assert tinkoff.gen_token(base, password="p") == tinkoff.gen_token(
        with_nested, password="p"
    )


def test_verify_notification_roundtrip(monkeypatch) -> None:
    # Подпись читает пароль из настроек, зарегистрированных в auth-billing-core.
    from app.core.config import settings

    monkeypatch.setattr(settings, "tinkoff_password", "secret")
    payload = {"TerminalKey": "T", "OrderId": "o", "Success": True, "Status": "CONFIRMED"}
    payload["Token"] = tinkoff.gen_token(payload)
    assert tinkoff.verify_notification(payload) is True
    payload["Token"] = "bad"
    assert tinkoff.verify_notification(payload) is False
