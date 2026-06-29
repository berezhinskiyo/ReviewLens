"""Обёртка над OpenAI SDK с подсчётом фактической стоимости по usage.

Все суммы — в копейках (int). Используем Chat Completions с принудительным
JSON-ответом (response_format json_object).
"""

import json
import re
from dataclasses import dataclass, field

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logging import logger

# Цены за 1M токенов в USD (вход, выход). Источник — прайс OpenAI.
MODEL_PRICING_USD: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
}

# Курс USD→RUB для оценки экономики.
USD_TO_RUB = 95.0


def _price_for(model: str) -> tuple[float, float]:
    for key, price in MODEL_PRICING_USD.items():
        if model.startswith(key):
            return price
    return (0.15, 0.60)


def cost_kopecks(model: str, input_tokens: int, output_tokens: int) -> int:
    in_price, out_price = _price_for(model)
    usd = (input_tokens / 1_000_000) * in_price + (output_tokens / 1_000_000) * out_price
    return round(usd * USD_TO_RUB * 100)


@dataclass
class LLMUsage:
    """Накопитель токенов и стоимости по всему пайплайну."""

    input_tokens: int = 0
    output_tokens: int = 0
    cost_kopecks: int = 0
    calls: int = 0
    per_model: dict[str, int] = field(default_factory=dict)

    def add(self, model: str, in_tok: int, out_tok: int) -> None:
        self.input_tokens += in_tok
        self.output_tokens += out_tok
        self.calls += 1
        c = cost_kopecks(model, in_tok, out_tok)
        self.cost_kopecks += c
        self.per_model[model] = self.per_model.get(model, 0) + c


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def extract_json(text: str) -> object:
    """Достаёт JSON из ответа модели, терпимо к ```-обрамлению и мусору."""
    text = text.strip()
    fence = _JSON_FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = next((i for i, ch in enumerate(text) if ch in "[{"), None)
        if start is None:
            raise
        for end in range(len(text), start, -1):
            chunk = text[start:end]
            try:
                return json.loads(chunk)
            except json.JSONDecodeError:
                continue
        raise


class LLMClient:
    def __init__(self, usage: LLMUsage | None = None) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.usage = usage or LLMUsage()

    async def complete_json(
        self, *, model: str, system: str, user: str, max_tokens: int = 4096
    ) -> object:
        """Один вызов модели, ожидаем JSON в ответе. Учитываем usage.

        response_format=json_object требует, чтобы слово JSON встречалось
        в сообщениях — наши системные промпты это гарантируют.
        """
        resp = await self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        if resp.usage:
            self.usage.add(model, resp.usage.prompt_tokens, resp.usage.completion_tokens)

        text = resp.choices[0].message.content or ""
        try:
            return extract_json(text)
        except json.JSONDecodeError:
            logger.error("llm.json_parse_failed", model=model, preview=text[:300])
            raise

    async def aclose(self) -> None:
        await self._client.close()
