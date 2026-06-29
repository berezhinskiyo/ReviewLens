"""E2E-тест промптов на сохранённой фикстуре отзывов (ТЗ 6.4).

Позволяет итеративно улучшать промпты, не парся карточку каждый раз.
Запуск (нужен ключ): OPENAI_API_KEY=... pytest -k prompts_e2e -s
"""

import json
import os
from pathlib import Path

import pytest

from app.llm.pipeline import run_pipeline
from app.scrapers.base import ScrapedProduct, ScrapedReview

FIXTURE = Path(__file__).parent / "fixtures" / "sample_reviews.json"


def _load_fixture() -> tuple[ScrapedProduct, list[ScrapedReview]]:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    p = data["product"]
    product = ScrapedProduct(
        marketplace=p["marketplace"],
        external_id=p["external_id"],
        url=p["url"],
        title=p.get("title"),
        brand=p.get("brand"),
        category=p.get("category"),
        rating=p.get("rating"),
        reviews_count=p.get("reviews_count"),
    )
    reviews = [
        ScrapedReview(
            external_id=r["external_id"],
            rating=r.get("rating"),
            text=r.get("text"),
            pros=r.get("pros"),
            cons=r.get("cons"),
        )
        for r in data["reviews"]
    ]
    return product, reviews


def test_fixture_loads() -> None:
    product, reviews = _load_fixture()
    assert product.external_id == "12345678"
    assert len(reviews) >= 10


@pytest.mark.skipif(
    not os.getenv("RUN_LLM_E2E"), reason="нужен RUN_LLM_E2E=1 (тратит токены OpenAI)"
)
async def test_pipeline_e2e() -> None:
    product, reviews = _load_fixture()
    result, usage = await run_pipeline(product, reviews)

    assert result.summary
    assert result.product_info.reviews_analyzed == len(reviews)
    # На фикстуре чётко видны жалобы на тонкую ткань и пошив
    assert result.complaints or result.praises
    assert result.opportunities

    # Контроль экономики: на маленькой фикстуре стоимость заведомо мала
    print(f"\nСтоимость анализа: {usage.cost_kopecks / 100:.2f} ₽, вызовов: {usage.calls}")
    assert usage.cost_kopecks >= 0
