import re
from datetime import datetime, timezone

from app.core.logging import logger
from app.scrapers.base import (
    BaseScraper,
    ScrapedProduct,
    ScrapedReview,
    ScrapeResult,
    ScraperError,
)

# https://www.wildberries.ru/catalog/{article}/detail.aspx
_ARTICLE_RE = re.compile(r"/catalog/(\d+)/")
_ARTICLE_FALLBACK_RE = re.compile(r"(?:nm=|article=|/)(\d{6,})")


class WildberriesScraper(BaseScraper):
    marketplace = "wb"

    CARD_URL = (
        "https://card.wb.ru/cards/v1/detail"
        "?appType=1&curr=rub&dest=-1257786&nm={article}"
    )
    FEEDBACKS_URL = "https://feedbacks{host}.wb.ru/feedbacks/v1/{imt_id}"

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
        data = await self.get_json(self.CARD_URL.format(article=article))
        products = (data or {}).get("data", {}).get("products", [])
        if not products:
            raise ScraperError(f"Карточка WB {article} не найдена или недоступна.")
        p = products[0]

        imt_id = str(p.get("root", ""))
        if not imt_id:
            raise ScraperError(f"Не удалось получить imt_id (root) для {article}.")

        # Цена WB в копейках уже (salePriceU/priceU — в копейках)
        price = p.get("salePriceU") or p.get("priceU")
        rating = p.get("reviewRating") or p.get("rating")

        product = ScrapedProduct(
            marketplace=self.marketplace,
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

    async def _fetch_feedbacks(self, imt_id: str, max_reviews: int) -> list[ScrapedReview]:
        """Отзывы доступны с двух хостов; мержим и дедуплицируем по id."""
        seen: dict[str, ScrapedReview] = {}
        for host in (1, 2):
            url = self.FEEDBACKS_URL.format(host=host, imt_id=imt_id)
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
