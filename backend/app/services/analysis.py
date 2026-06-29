"""Бизнес-логика анализа: кэш карточки, парсинг, прогон LLM, сохранение."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.db.models import Analysis, Product, Review, User
from app.llm.pipeline import run_pipeline
from app.scrapers.base import ScrapedProduct, ScrapedReview
from app.scrapers.registry import detect_marketplace, get_scraper

CACHE_TTL = timedelta(hours=24)


class AnalysisError(Exception):
    pass


async def _get_cached_product(
    db: AsyncSession, marketplace: str, external_id: str
) -> Product | None:
    result = await db.execute(
        select(Product).where(
            Product.marketplace == marketplace, Product.external_id == external_id
        )
    )
    product = result.scalar_one_or_none()
    if product is None or product.last_parsed_at is None:
        return None
    if datetime.now(timezone.utc) - product.last_parsed_at > CACHE_TTL:
        return None
    return product


async def _upsert_product(db: AsyncSession, sp: ScrapedProduct) -> Product:
    result = await db.execute(
        select(Product).where(
            Product.marketplace == sp.marketplace, Product.external_id == sp.external_id
        )
    )
    product = result.scalar_one_or_none()
    if product is None:
        product = Product(marketplace=sp.marketplace, external_id=sp.external_id, url=sp.url)
        db.add(product)

    product.url = sp.url
    product.title = sp.title
    product.brand = sp.brand
    product.category = sp.category
    product.price_kopecks = sp.price_kopecks
    product.rating = sp.rating
    product.reviews_count = sp.reviews_count
    product.last_parsed_at = datetime.now(timezone.utc)
    await db.flush()
    return product


async def _save_reviews(
    db: AsyncSession, product_id: uuid.UUID, reviews: list[ScrapedReview]
) -> None:
    if not reviews:
        return
    rows = [
        {
            "product_id": product_id,
            "external_id": r.external_id,
            "rating": r.rating,
            "text": r.text,
            "pros": r.pros,
            "cons": r.cons,
            "review_date": r.review_date,
        }
        for r in reviews
    ]
    stmt = pg_insert(Review).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=["product_id", "external_id"])
    await db.execute(stmt)


async def _load_cached_reviews(
    db: AsyncSession, product_id: uuid.UUID
) -> list[ScrapedReview]:
    result = await db.execute(
        select(Review)
        .where(Review.product_id == product_id)
        .order_by(Review.review_date.desc().nullslast())
        .limit(settings.max_reviews_per_analysis)
    )
    return [
        ScrapedReview(
            external_id=r.external_id,
            rating=r.rating,
            text=r.text,
            pros=r.pros,
            cons=r.cons,
            review_date=r.review_date,
        )
        for r in result.scalars().all()
    ]


def _product_to_scraped(p: Product) -> ScrapedProduct:
    return ScrapedProduct(
        marketplace=p.marketplace,
        external_id=p.external_id,
        url=p.url,
        title=p.title,
        brand=p.brand,
        category=p.category,
        price_kopecks=p.price_kopecks,
        rating=float(p.rating) if p.rating is not None else None,
        reviews_count=p.reviews_count,
    )


async def process_analysis(db: AsyncSession, analysis_id: uuid.UUID) -> None:
    """Полный цикл обработки анализа воркером.

    pending → scraping → analyzing → completed | failed.
    При ошибке анализ из лимита НЕ списывается (списываем только при completed).
    """
    analysis = await db.get(Analysis, analysis_id)
    if analysis is None:
        logger.error("analysis.not_found", analysis_id=str(analysis_id))
        return

    try:
        marketplace = detect_marketplace(analysis.input_url)
        scraper = get_scraper(marketplace)
        external_id = scraper.parse_url(analysis.input_url)

        # --- scraping (с учётом кэша) ---
        analysis.status = "scraping"
        await db.commit()

        cached = await _get_cached_product(db, marketplace, external_id)
        if cached is not None:
            logger.info("analysis.cache_hit", product_id=str(cached.id))
            product = cached
            sp = _product_to_scraped(cached)
            reviews = await _load_cached_reviews(db, cached.id)
        else:
            async with scraper:
                scrape_result = await scraper.scrape(
                    analysis.input_url, settings.max_reviews_per_analysis
                )
            sp = scrape_result.product
            reviews = scrape_result.reviews
            product = await _upsert_product(db, sp)
            await _save_reviews(db, product.id, reviews)
            await db.commit()

        analysis.product_id = product.id

        # --- analyzing ---
        analysis.status = "analyzing"
        await db.commit()

        result, usage = await run_pipeline(sp, reviews)

        analysis.result = result.model_dump()
        analysis.reviews_analyzed_count = result.product_info.reviews_analyzed
        analysis.llm_cost_kopecks = usage.cost_kopecks
        analysis.status = "completed"
        analysis.completed_at = datetime.now(timezone.utc)

        # Списываем анализ из лимита ТОЛЬКО при успехе
        user = await db.get(User, analysis.user_id)
        if user is not None:
            user.analyses_used_this_period += 1

        await db.commit()
        logger.info(
            "analysis.completed",
            analysis_id=str(analysis_id),
            cost_kopecks=usage.cost_kopecks,
            reviews=analysis.reviews_analyzed_count,
        )

    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        analysis = await db.get(Analysis, analysis_id)
        if analysis is not None:
            analysis.status = "failed"
            analysis.error_message = str(exc)[:1000]
            await db.commit()
        logger.exception("analysis.failed", analysis_id=str(analysis_id), error=str(exc))
