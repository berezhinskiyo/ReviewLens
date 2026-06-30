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

# https://megamarket.ru/catalog/details/...-_{goodsId}/  или .../{goodsId}/
_GOODS_RE = re.compile(r"(?:_|/)(\d{6,})/?(?:\?|$)")
_ANY_LONG_NUM = re.compile(r"(\d{8,})")

BASE = "https://megamarket.ru/api/mobile/v1/catalogService"


class MegamarketScraper(BaseScraper):
    """Мегамаркет через mobile JSON-API (как WB, без браузера).

    Важно: API проверяет репутацию IP («отключите VPN», code 7) — стабильно
    работает с чистого РФ-IP (прод-сервер). Из подозрительных сетей вернёт ошибку.
    """

    marketplace = "megamarket"

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Origin": "https://megamarket.ru",
            "Referer": "https://megamarket.ru/",
        }

    def parse_url(self, url: str) -> str:
        m = _GOODS_RE.search(url) or _ANY_LONG_NUM.search(url)
        if not m:
            raise ScraperError(
                "Не удалось распознать товар Мегамаркета в ссылке. "
                "Нужна ссылка вида megamarket.ru/catalog/details/...-_100012345678/"
            )
        return m.group(1)

    async def _post_json(self, path: str, payload: dict, *, retries: int = 3):
        # Дублируем логику get_json, но POST'ом.
        import asyncio

        last_exc = None
        for attempt in range(retries):
            await self._throttle()
            try:
                resp = await self._client.post(
                    f"{BASE}{path}", headers=self._headers(), json=payload
                )
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, dict) and data.get("code") == 7:
                    raise ScraperError(
                        "Мегамаркет отклонил запрос (проверка IP). На сервере в РФ "
                        "обычно работает; из этой сети — заблокировано."
                    )
                return data
            except ScraperError:
                raise
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                await asyncio.sleep(2**attempt)
        raise ScraperError(f"Мегамаркет недоступен: {last_exc}")

    async def _fetch_card(self, goods_id: str) -> ScrapedProduct:
        data = await self._post_json("/product/get", {"goodsId": goods_id})
        item = {}
        if isinstance(data, dict):
            item = data.get("item") or data.get("product") or data.get("goods") or data
        return ScrapedProduct(
            marketplace=self.marketplace,
            external_id=goods_id,
            url=f"https://megamarket.ru/catalog/details/{goods_id}/",
            title=item.get("title") or item.get("goodsName") or item.get("name"),
            brand=(item.get("brand") or {}).get("title")
            if isinstance(item.get("brand"), dict)
            else item.get("brand"),
            rating=_as_float(item.get("rating") or item.get("averageRating")),
            reviews_count=item.get("reviewsCount"),
        )

    async def _fetch_reviews(self, goods_id: str, max_reviews: int) -> list[ScrapedReview]:
        out: dict[str, ScrapedReview] = {}
        page = 1
        while len(out) < max_reviews and page <= 30:
            data = await self._post_json(
                "/product/reviews/list",
                {
                    "goodsId": goods_id,
                    "reviewsCount": 50,
                    "pageNumber": page,
                    "sortType": 1,
                    "paginationMode": "PAGE",
                    "reviewsType": "ALL",
                },
            )
            items = []
            if isinstance(data, dict):
                items = data.get("reviews") or data.get("items") or []
            if not items:
                break
            for raw in items:
                rid = str(raw.get("id") or raw.get("reviewId") or len(out))
                if rid in out:
                    continue
                out[rid] = _map_review(rid, raw)
                if len(out) >= max_reviews:
                    break
            page += 1
        return list(out.values())[:max_reviews]

    async def scrape(self, url: str, max_reviews: int) -> ScrapeResult:
        goods_id = self.parse_url(url)
        logger.info("megamarket.scrape.start", goods_id=goods_id)
        try:
            product = await self._fetch_card(goods_id)
        except ScraperError:
            product = ScrapedProduct(
                marketplace=self.marketplace,
                external_id=goods_id,
                url=url,
            )
        reviews = await self._fetch_reviews(goods_id, max_reviews)
        if not reviews:
            raise ScraperError("У этого товара нет отзывов либо они недоступны.")
        logger.info("megamarket.scrape.done", goods_id=goods_id, reviews=len(reviews))
        return ScrapeResult(product=product, reviews=reviews)


def _as_float(v) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _map_review(rid: str, raw: dict) -> ScrapedReview:
    date = None
    raw_date = raw.get("date") or raw.get("createdAt") or raw.get("created")
    if raw_date:
        try:
            date = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            date = None
    rating = raw.get("rating") or raw.get("grade") or raw.get("mark")
    return ScrapedReview(
        external_id=rid,
        rating=int(rating) if isinstance(rating, (int, float)) else None,
        text=raw.get("text") or raw.get("comment") or None,
        pros=raw.get("pros") or raw.get("plus") or None,
        cons=raw.get("cons") or raw.get("minus") or None,
        review_date=date,
    )
