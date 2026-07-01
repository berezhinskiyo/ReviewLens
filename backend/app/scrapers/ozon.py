import re
from datetime import datetime

from app.scrapers.base import ScrapedProduct, ScrapedReview, ScrapeResult, ScraperError
from app.scrapers.playwright_base import PageCapture, PlaywrightScraper, deep_find_lists

# https://www.ozon.ru/product/nazvanie-tovara-1234567890/
_SKU_RE = re.compile(r"/product/[^/]*?-(\d{5,})/?")
_ANY_NUM = re.compile(r"(\d{6,})")

# Строгие ключи: настоящий отзыв Ozon содержит content.comment/positive/negative
_REVIEW_KEYS = ("comment", "positive", "negative", "reviewuuid", "authorname")


class OzonScraper(PlaywrightScraper):
    """Ozon: SPA + анти-бот. Берём отзывы из composer-api/entrypoint XHR через браузер."""

    marketplace = "ozon"
    CAPTURE_URL_NEEDLES = (
        "composer-api",
        "entrypoint-api",
        "page/json/v2",
        "webListReviews",
        "/reviews",
    )

    def parse_url(self, url: str) -> str:
        m = _SKU_RE.search(url) or _ANY_NUM.search(url)
        if not m:
            raise ScraperError(
                "Не удалось распознать товар Ozon. Нужна ссылка вида "
                "ozon.ru/product/nazvanie-1234567890/"
            )
        return m.group(1)

    def _target_url(self, url: str) -> str:
        base = url.split("?")[0].rstrip("/")
        return f"{base}/reviews/"

    def parse_capture(self, external_id: str, url: str, cap: PageCapture) -> ScrapeResult:
        product = ScrapedProduct(
            marketplace=self.marketplace,
            external_id=external_id,
            url=url,
            title=_extract_title(cap.html),
        )
        reviews: dict[str, ScrapedReview] = {}
        for payload in cap.matching(*self.CAPTURE_URL_NEEDLES):
            for raw in deep_find_lists(payload, _REVIEW_KEYS):
                rid = str(raw.get("uuid") or raw.get("id") or len(reviews))
                if rid in reviews:
                    continue
                mapped = _map_ozon_review(rid, raw)
                if mapped:
                    reviews[rid] = mapped
        return ScrapeResult(product=product, reviews=list(reviews.values()))


def _extract_title(html: str) -> str | None:
    m = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).split(" - ")[0].strip() or None
    return None


def _map_ozon_review(rid: str, raw: dict) -> ScrapedReview | None:
    content = raw.get("content") if isinstance(raw.get("content"), dict) else raw
    # настоящий отзыв: есть comment/positive/negative (а не просто «text» тултипа)
    text = content.get("comment")
    pros = content.get("positive") or content.get("pros")
    cons = content.get("negative") or content.get("cons")
    if not (text or pros or cons):
        return None
    # отсекаем UI-объекты: у отзыва должен быть автор или оценка
    if raw.get("score") is None and content.get("score") is None and not raw.get("author"):
        return None
    score = raw.get("score") or raw.get("rating") or content.get("score")
    date = None
    raw_date = raw.get("publishedAt") or raw.get("createdAt") or raw.get("date")
    if raw_date:
        try:
            date = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            date = None
    return ScrapedReview(
        external_id=rid,
        rating=int(score) if isinstance(score, (int, float)) else None,
        text=text or None,
        pros=pros or None,
        cons=cons or None,
        review_date=date,
    )
