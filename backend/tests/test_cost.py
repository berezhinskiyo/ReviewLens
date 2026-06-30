from app.llm.openai_client import LLMUsage, cost_kopecks, extract_json


def test_cost_gemini_flash_lite() -> None:
    # 1M входных + 1M выходных = 10.06 + 40.23 ₽ → копейки
    c = cost_kopecks("google/gemini-2.5-flash-lite", 1_000_000, 1_000_000)
    assert c == round((10.06 + 40.23) * 100)


def test_cost_uses_router_cost_rub() -> None:
    # Если роутер вернул фактическую стоимость — берём её, а не прайс-таблицу
    usage = LLMUsage()
    usage.add("deepseek/deepseek-v3.2", 1000, 500, cost_rub=0.0123)
    assert usage.cost_kopecks == round(0.0123 * 100)


def test_cost_accumulates() -> None:
    usage = LLMUsage()
    usage.add("google/gemini-2.5-flash-lite", 30_000, 5_000)
    usage.add("deepseek/deepseek-v3.2", 10_000, 2_000)
    assert usage.calls == 2
    assert usage.cost_kopecks > 0
    assert set(usage.per_model) == {
        "google/gemini-2.5-flash-lite",
        "deepseek/deepseek-v3.2",
    }


def test_extract_json_plain() -> None:
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_fenced() -> None:
    text = "```json\n{\"clusters\": [{\"topic\": \"x\"}]}\n```"
    assert extract_json(text) == {"clusters": [{"topic": "x"}]}


def test_extract_json_with_noise() -> None:
    text = 'Вот результат: {"a": 1} надеюсь помог'
    assert extract_json(text) == {"a": 1}
