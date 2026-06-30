import random
import re
from datetime import datetime, timezone

from app.core.logging import logger
from app.scrapers.base import (
    USER_AGENTS,
    BaseScraper,
    ScrapedProduct,
    ScrapedReview,
    ScrapeResult,
    ScraperError,
)

# https://www.wildberries.ru/catalog/{article}/detail.aspx
_ARTICLE_RE = re.compile(r"/catalog/(\d+)/")
_ARTICLE_FALLBACK_RE = re.compile(r"(?:nm=|article=|/)(\d{6,})")


def _basket_host(vol: int) -> str:
    """Маппинг vol → номер basket-хоста CDN WB (для fallback card.json).

    Диапазоны растут по мере добавления хранилищ WB; при необходимости —
    дополнить верхнюю границу.
    """
    ranges = [
        (143, "01"), (287, "02"), (431, "03"), (719, "04"), (1007, "05"),
        (1061, "06"), (1115, "07"), (1169, "08"), (1313, "09"), (1601, "10"),
        (1655, "11"), (1919, "12"), (2045, "13"), (2189, "14"), (2405, "15"),
        (2621, "16"), (2837, "17"), (3053, "18"), (3269, "19"), (3485, "20"),
        (3701, "21"), (3917, "22"), (4133, "23"), (4349, "24"), (4565, "25"),
        (4877, "26"), (5189, "27"), (5501, "28"), (5813, "29"), (6125, "30"),
        (6437, "31"), (6749, "32"), (7061, "33"), (7373, "34"), (7685, "35"),
        (7997, "36"), (8309, "37"), (8621, "38"), (8933, "39"), (9245, "40"),
    ]
    for limit, host in ranges:
        if vol <= limit:
            return host
    return "41"


class WildberriesScraper(BaseScraper):
    marketplace = "wb"

    # v1 устарел и отдаёт 403 — используем v2
    CARD_URL = (
        "https://card.wb.ru/cards/v2/detail"
        "?appType=1&curr=rub&dest=-1257786&spp=30&nm={article}"
    )
    FEEDBACKS_V1 = "https://feedbacks{host}.wb.ru/feedbacks/v1/{imt_id}"
    FEEDBACKS_V2 = "https://feedbacks{host}.wb.ru/feedbacks/v2/{imt_id}"

    def _headers(self) -> dict[str, str]:
        # WB пропускает запросы только с «браузерными» заголовками
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Origin": "https://www.wildberries.ru",
            "Referer": "https://www.wildberries.ru/",
        }

    def parse_url(self, url: str) -> str:
        match = _ARTICLE_RE.search(url)
        if not match:
            match = _ARTICLE_FALLBACK_RE.search(url)
        if not match:
            raise ScraperError(
                "Не удалось распознать артикул WB в URL. "
                "Ожидается ссылка вида wildberries.ru/catalog/12345678/detail.aspx"
            )
        return match.group(1)

    async def _fetch_card(self, article: str) -> tuple[ScrapedProduct, str]:
        # 1) Основной источник — basket CDN card.json (надёжно отдаёт imt_id/title/brand).
        #    card.wb.ru/detail часто отдаёт 403/404 в зависимости от сети.
        product, imt_id = await self._fetch_card_basket(article)

        # 2) Обогащаем цену/рейтинг из card.wb.ru/v2/detail (необязательно, fail-fast).
        try:
            data = await self.get_json(self.CARD_URL.format(article=article), retries=1)
            products = (data or {}).get("data", {}).get("products", [])
            if products:
                detail_product, detail_imt = _parse_detail(
                    article, products[0], self.marketplace
                )
                if product is None:
                    product, imt_id = detail_product, detail_imt
                else:
                    # дополняем недостающее из detail
                    product.price_kopecks = detail_product.price_kopecks
                    product.rating = detail_product.rating
                    product.reviews_count = detail_product.reviews_count
                    if not product.title:
                        product.title = detail_product.title
                    if not product.brand:
                        product.brand = detail_product.brand
                    imt_id = imt_id or detail_imt
        except ScraperError as exc:
            logger.warning("wb.card.detail_failed", article=article, error=str(exc))

        if not imt_id or product is None:
            raise ScraperError(
                f"Карточка WB {article} не найдена или временно недоступна."
            )
        return product, imt_id

    async def _fetch_card_basket(self, article: str) -> tuple[ScrapedProduct | None, str]:
        try:
            nm = int(article)
        except ValueError:
            return None, ""
        vol = nm // 100_000
        part = nm // 1_000
        host = _basket_host(vol)
        url = (
            f"https://basket-{host}.wbbasket.ru/vol{vol}/part{part}/{nm}/info/ru/card.json"
        )
        try:
            data = await self.get_json(url)
        except ScraperError:
            return None, ""
        if not isinstance(data, dict):
            return None, ""

        imt_id = str(data.get("imt_id") or "")
        if not imt_id:
            return None, ""
        selling = data.get("selling") or {}
        product = ScrapedProduct(
            marketplace=self.marketplace,
            external_id=article,
            url=f"https://www.wildberries.ru/catalog/{article}/detail.aspx",
            title=data.get("imt_name") or data.get("subj_name"),
            brand=selling.get("brand_name"),
            category=data.get("subj_name"),
        )
        return product, imt_id

    async def _fetch_feedbacks(self, imt_id: str, max_reviews: int) -> list[ScrapedReview]:
        """Отзывы доступны с двух хостов; пробуем v1, затем v2; мержим и дедуплицируем."""
        seen: dict[str, ScrapedReview] = {}
        for template in (self.FEEDBACKS_V1, self.FEEDBACKS_V2):
            for host in (1, 2):
                url = template.format(host=host, imt_id=imt_id)
                try:
                    data = await self.get_json(url)
                except ScraperError:
                    continue
                if not data:
                    continue
                for raw in (data.get("feedbacks") or []):
                    ext_id = str(raw.get("id") or raw.get("globalUserId") or "")
                    if not ext_id or ext_id in seen:
                        continue
                    seen[ext_id] = _map_review(ext_id, raw)
                    if len(seen) >= max_reviews:
                        break
                if len(seen) >= max_reviews:
                    break
            if seen:
                break

        reviews = sorted(
            seen.values(),
            key=lambda r: r.review_date or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return reviews[:max_reviews]

    async def scrape(self, url: str, max_reviews: int) -> ScrapeResult:
        article = self.parse_url(url)
        logger.info("wb.scrape.start", article=article)

        product, imt_id = await self._fetch_card(article)
        reviews = await self._fetch_feedbacks(imt_id, max_reviews)

        if not reviews:
            raise ScraperError(
                "У этой карточки нет отзывов либо они недоступны для анализа."
            )

        logger.info("wb.scrape.done", article=article, reviews=len(reviews))
        return ScrapeResult(product=product, reviews=reviews)


def _parse_detail(article: str, p: dict, marketplace: str) -> tuple[ScrapedProduct, str]:
    imt_id = str(p.get("root", ""))

    # v2: цена в sizes[].price.{product|basic} (в копейках); v1: salePriceU/priceU
    price = None
    sizes = p.get("sizes") or []
    if sizes:
        price_obj = (sizes[0].get("price") or {}) if isinstance(sizes[0], dict) else {}
        price = price_obj.get("product") or price_obj.get("basic")
    if not price:
        price = p.get("salePriceU") or p.get("priceU")

    rating = p.get("reviewRating") or p.get("nmReviewRating") or p.get("rating")

    product = ScrapedProduct(
        marketplace=marketplace,
        external_id=article,
        url=f"https://www.wildberries.ru/catalog/{article}/detail.aspx",
        title=p.get("name"),
        brand=p.get("brand"),
        category=p.get("entity") or p.get("subjectName"),
        price_kopecks=int(price) if price else None,
        rating=float(rating) if rating else None,
        reviews_count=p.get("feedbacks"),
    )
    return product, imt_id


def _map_review(ext_id: str, raw: dict) -> ScrapedReview:
    pros = raw.get("pros") or None
    cons = raw.get("cons") or None
    text = raw.get("text") or None

    review_date = None
    raw_date = raw.get("createdDate") or raw.get("date")
    if raw_date:
        try:
            review_date = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            review_date = None

    return ScrapedReview(
        external_id=ext_id,
        rating=raw.get("productValuation") or raw.get("rating"),
        text=text,
        pros=pros,
        cons=cons,
        review_date=review_date,
    )
