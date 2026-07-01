import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from app.core.logging import logger

# Реальные User-Agent'ы для ротации (анти-блокировка)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.0.0",
]


@dataclass
class ScrapedProduct:
    marketplace: str
    external_id: str
    url: str
    title: str | None = None
    brand: str | None = None
    category: str | None = None
    price_kopecks: int | None = None
    rating: float | None = None
    reviews_count: int | None = None


@dataclass
class ScrapedReview:
    external_id: str | None
    rating: int | None = None
    text: str | None = None
    pros: str | None = None
    cons: str | None = None
    review_date: datetime | None = None


@dataclass
class ScrapeResult:
    product: ScrapedProduct
    reviews: list[ScrapedReview] = field(default_factory=list)


class ScraperError(Exception):
    """Ошибка парсинга (невалидный URL, недоступная карточка и т.п.)."""


class BaseScraper:
    """Общая логика: rate limit ≤ 2 RPS на хост, retry с backoff, UA-ротация."""

    marketplace: str = ""
    _min_interval = 0.5  # 2 RPS
    _last_request_at = 0.0
    _lock = asyncio.Lock()

    def __init__(self) -> None:
        from app.core.config import settings

        proxy = settings.scraper_proxy or None
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(20.0), follow_redirects=True, proxy=proxy
        )

    async def __aenter__(self) -> "BaseScraper":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru-RU,ru;q=0.9",
        }

    async def _throttle(self) -> None:
        async with BaseScraper._lock:
            elapsed = asyncio.get_event_loop().time() - BaseScraper._last_request_at
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            BaseScraper._last_request_at = asyncio.get_event_loop().time()

    async def get_json(self, url: str, *, retries: int = 3) -> dict | list | None:
        """GET с throttle, ретраями и экспоненциальным backoff."""
        last_exc: Exception | None = None
        for attempt in range(retries):
            await self._throttle()
            try:
                resp = await self._client.get(url, headers=self._headers())
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_exc = exc
                backoff = 2**attempt + random.uniform(0, 0.5)
                logger.warning(
                    "scraper.retry",
                    url=url,
                    attempt=attempt + 1,
                    error=str(exc),
                    backoff=round(backoff, 2),
                )
                await asyncio.sleep(backoff)
        raise ScraperError(f"Не удалось загрузить {url}: {last_exc}")

    def parse_url(self, url: str) -> str:
        """Извлечь external_id (артикул/SKU) из URL карточки."""
        raise NotImplementedError

    async def scrape(self, url: str, max_reviews: int) -> ScrapeResult:
        raise NotImplementedError
