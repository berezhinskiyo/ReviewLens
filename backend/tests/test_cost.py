from app.llm.openai_client import LLMUsage, cost_kopecks, extract_json


def test_cost_gpt4o_mini() -> None:
    # 1M входных + 1M выходных gpt-4o-mini = 0.15$ + 0.60$ = 0.75$ * 95 * 100 копеек
    c = cost_kopecks("gpt-4o-mini", 1_000_000, 1_000_000)
    assert c == round(0.75 * 95.0 * 100)


def test_cost_accumulates() -> None:
    usage = LLMUsage()
    usage.add("gpt-4o-mini", 30_000, 5_000)
    usage.add("gpt-4o", 10_000, 2_000)
    assert usage.calls == 2
    assert usage.cost_kopecks > 0
    assert set(usage.per_model) == {"gpt-4o-mini", "gpt-4o"}


def test_extract_json_plain() -> None:
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_fenced() -> None:
    text = "```json\n{\"clusters\": [{\"topic\": \"x\"}]}\n```"
    assert extract_json(text) == {"clusters": [{"topic": "x"}]}


def test_extract_json_with_noise() -> None:
    text = 'Вот результат: {"a": 1} надеюсь помог'
    assert extract_json(text) == {"a": 1}
