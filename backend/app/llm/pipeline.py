"""Оркестрация анализа: Extract → Cluster → Synthesize.

Стратегия (ТЗ 6.1):
- массовая обработка чанков — Haiku (дёшево, быстро);
- итоговый синтез — Sonnet (один вызов).
Цель: <= 15 ₽ на анализ 300 отзывов.
"""

import asyncio
from datetime import datetime, timezone

from app.core.config import settings
from app.core.logging import logger
from app.llm.openai_client import LLMClient, LLMUsage
from app.llm import prompts
from app.scrapers.base import ScrapedProduct, ScrapedReview
from app.schemas.result import AnalysisResult

EXTRACT_CHUNK_SIZE = 30
EXTRACT_CONCURRENCY = 5  # параллельные вызовы Haiku


def _review_to_text(idx: int, r: ScrapedReview) -> str:
    parts: list[str] = []
    if r.rating:
        parts.append(f"оценка {r.rating}/5")
    if r.pros:
        parts.append(f"Достоинства: {r.pros}")
    if r.cons:
        parts.append(f"Недостатки: {r.cons}")
    if r.text:
        parts.append(f"Текст: {r.text}")
    body = " | ".join(parts) if parts else "(пустой отзыв)"
    return f"[{idx}] {body}"


def _chunks(reviews: list[ScrapedReview], size: int) -> list[list[ScrapedReview]]:
    return [reviews[i : i + size] for i in range(0, len(reviews), size)]


async def _extract_chunk(
    client: LLMClient, chunk: list[ScrapedReview]
) -> tuple[list[str], list[str]]:
    reviews_block = "\n".join(_review_to_text(i, r) for i, r in enumerate(chunk))
    user = prompts.EXTRACT_USER_TEMPLATE.format(n=len(chunk), reviews_block=reviews_block)
    try:
        data = await client.complete_json(
            model=settings.openai_model_extract,
            system=prompts.EXTRACT_SYSTEM,
            user=user,
            max_tokens=4096,
        )
    except Exception as exc:  # noqa: BLE001 — один сбойный чанк не валит весь анализ
        logger.warning("pipeline.extract_chunk_failed", error=str(exc))
        return [], []

    negative: list[str] = []
    positive: list[str] = []
    items = data.get("reviews", []) if isinstance(data, dict) else data
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            negative.extend(str(c) for c in item.get("claims_negative", []) if c)
            positive.extend(str(c) for c in item.get("claims_positive", []) if c)
    return negative, positive


async def _cluster(
    client: LLMClient, claims: list[str], *, positive: bool
) -> list[dict]:
    if not claims:
        return []
    claims_block = "\n".join(f"- {c}" for c in claims)
    template = (
        prompts.CLUSTER_POSITIVE_TEMPLATE if positive else prompts.CLUSTER_NEGATIVE_TEMPLATE
    )
    user = template.format(claims_block=claims_block)
    try:
        data = await client.complete_json(
            model=settings.openai_model_cluster,
            system=prompts.CLUSTER_SYSTEM,
            user=user,
            max_tokens=4096,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("pipeline.cluster_failed", positive=positive, error=str(exc))
        return []
    clusters = data.get("clusters", []) if isinstance(data, dict) else data
    return [d for d in clusters if isinstance(d, dict)] if isinstance(clusters, list) else []


def _format_clusters(clusters: list[dict], *, with_severity: bool) -> str:
    if not clusters:
        return "(нет данных)"
    lines = []
    for c in clusters:
        topic = c.get("topic", "?")
        freq = c.get("frequency", 0)
        quotes = "; ".join(str(q) for q in c.get("sample_quotes", [])[:3])
        sev = f" / severity={c.get('severity', 'medium')}" if with_severity else ""
        lines.append(f"- {topic} (частота {freq}{sev}): {quotes}")
    return "\n".join(lines)


def _trim_reviews_to_budget(reviews: list[ScrapedReview]) -> list[ScrapedReview]:
    """Грубая оценка токенов; при превышении бюджета берём свежие отзывы.

    Reviews уже отсортированы по дате (свежие первыми) в скрапере.
    """
    # ~ оценка: средний отзыв с extract ~ дешёвый, держим ориентир на бюджете.
    # Эвристика: ограничиваем верхнюю границу количества отзывов.
    max_reviews = settings.max_reviews_per_analysis
    if len(reviews) > max_reviews:
        logger.info("pipeline.trim", before=len(reviews), after=max_reviews)
        return reviews[:max_reviews]
    return reviews


async def run_pipeline(
    product: ScrapedProduct, reviews: list[ScrapedReview]
) -> tuple[AnalysisResult, LLMUsage]:
    reviews = _trim_reviews_to_budget(reviews)
    usage = LLMUsage()
    client = LLMClient(usage=usage)

    try:
        # --- Этап 1. Extract (параллельно по чанкам) ---
        chunks = _chunks(reviews, EXTRACT_CHUNK_SIZE)
        logger.info("pipeline.extract.start", chunks=len(chunks), reviews=len(reviews))

        sem = asyncio.Semaphore(EXTRACT_CONCURRENCY)

        async def _guarded(chunk: list[ScrapedReview]) -> tuple[list[str], list[str]]:
            async with sem:
                return await _extract_chunk(client, chunk)

        chunk_results = await asyncio.gather(*(_guarded(c) for c in chunks))

        negative: list[str] = []
        positive: list[str] = []
        for neg, pos in chunk_results:
            negative.extend(neg)
            positive.extend(pos)

        logger.info(
            "pipeline.extract.done", negative=len(negative), positive=len(positive)
        )

        # --- Этап 2. Cluster (параллельно negative / positive) ---
        neg_clusters, pos_clusters = await asyncio.gather(
            _cluster(client, negative, positive=False),
            _cluster(client, positive, positive=True),
        )

        # --- Этап 3. Synthesize (Sonnet, один вызов) ---
        synth_user = prompts.SYNTH_USER_TEMPLATE.format(
            title=product.title or "—",
            brand=product.brand or "—",
            rating=product.rating if product.rating is not None else "null",
            reviews_analyzed=len(reviews),
            complaints_block=_format_clusters(neg_clusters, with_severity=True),
            praises_block=_format_clusters(pos_clusters, with_severity=False),
        )
        synth_data = await client.complete_json(
            model=settings.openai_model_synth,
            system=prompts.SYNTH_SYSTEM,
            user=synth_user,
            max_tokens=8192,
        )
    finally:
        await client.aclose()

    result = _build_result(synth_data, product, len(reviews))
    logger.info(
        "pipeline.done",
        cost_kopecks=usage.cost_kopecks,
        calls=usage.calls,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
    )
    return result, usage


def _build_result(
    data: object, product: ScrapedProduct, reviews_analyzed: int
) -> AnalysisResult:
    """Валидируем ответ Sonnet через Pydantic, добиваем метаданными карточки."""
    payload = data if isinstance(data, dict) else {}

    # Гарантируем заполнение product_info из карточки
    pinfo = payload.get("product_info") or {}
    pinfo.setdefault("title", product.title)
    pinfo.setdefault("brand", product.brand)
    if pinfo.get("rating") is None:
        pinfo["rating"] = product.rating
    pinfo["reviews_analyzed"] = reviews_analyzed
    payload["product_info"] = pinfo
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()

    return AnalysisResult.model_validate(payload)
