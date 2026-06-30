import re
from datetime import datetime

from app.scrapers.base import ScrapedProduct, ScrapedReview, ScrapeResult, ScraperError
from app.scrapers.playwright_base import PageCapture, PlaywrightScraper, deep_find_lists

# https://www.avito.ru/.../nazvanie_1234567890
_ID_RE = re.compile(r"_(\d{6,})(?:\?|$|/)")
_ANY_NUM = re.compile(r"(\d{7,})")

# На Avito «отзывы» — это отзывы о продавце (рейтинг продавца).
_REVIEW_KEYS = ("text", "review", "score", "rating", "stage", "comment")


class AvitoScraper(PlaywrightScraper):
    """Avito (C2C): отзывы о продавце. Сильный анти-бот — на проде нужны прокси."""

    marketplace = "avito"
    CAPTURE_URL_NEEDLES = ("/ratings", "/reviews", "user/rating", "web/")
    SCROLLS = 10

    def parse_url(self, url: str) -> str:
        m = _ID_RE.search(url) or _ANY_NUM.search(url)
        if not m:
            raise ScraperError(
                "Не удалось распознать объявление Avito. Нужна ссылка вида "
                "avito.ru/gorod/kategoriya/nazvanie_1234567890"
            )
        return m.group(1)

    def parse_capture(self, external_id: str, url: str, cap: PageCapture) -> ScrapeResult:
        product = ScrapedProduct(
            marketplace=self.marketplace,
            external_id=external_id,
            url=url,
            title=_title(cap.html),
        )
        reviews: dict[str, ScrapedReview] = {}
        for payload in cap.matching(*self.CAPTURE_URL_NEEDLES):
            for raw in deep_find_lists(payload, _REVIEW_KEYS):
                rid = str(raw.get("id") or raw.get("itemId") or len(reviews))
                if rid in reviews:
                    continue
                mapped = _map(rid, raw)
                if mapped:
                    reviews[rid] = mapped
        return ScrapeResult(product=product, reviews=list(reviews.values()))


def _title(html: str) -> str | None:
    m = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return m.group(1).split(" - ")[0].strip() if m else None


def _map(rid: str, raw: dict) -> ScrapedReview | None:
    text = raw.get("text") or raw.get("comment") or raw.get("description")
    if not text or not isinstance(text, str):
        return None
    score = raw.get("score") or raw.get("rating") or raw.get("stars")
    date = None
    raw_date = raw.get("created") or raw.get("date") or raw.get("createdAt")
    if raw_date:
        try:
            # Avito иногда отдаёт unix-время
            if isinstance(raw_date, (int, float)):
                date = datetime.fromtimestamp(raw_date)
            else:
                date = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
        except (ValueError, TypeError, OSError):
            date = None
    return ScrapedReview(
        external_id=rid,
        rating=int(score) if isinstance(score, (int, float)) else None,
        text=text,
        review_date=date,
    )
