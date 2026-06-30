import re
from datetime import datetime

from app.scrapers.base import ScrapedProduct, ScrapedReview, ScrapeResult, ScraperError
from app.scrapers.playwright_base import PageCapture, PlaywrightScraper, deep_find_lists

# https://market.yandex.ru/product--nazvanie/123456789  или /product/123456789
_PID_RE = re.compile(r"/product(?:--[^/]*)?/(\d{5,})")
_ANY_NUM = re.compile(r"(\d{6,})")

_REVIEW_KEYS = ("text", "pro", "contra", "comment", "grade", "factors")


class YandexMarketScraper(PlaywrightScraper):
    """Яндекс.Маркет: SmartCaptcha + SPA. На проде, как правило, нужны прокси."""

    marketplace = "yandex"
    CAPTURE_URL_NEEDLES = ("resolveProductReviews", "/reviews", "api/resolve", "ProductReviews")
    SCROLLS = 10

    def parse_url(self, url: str) -> str:
        m = _PID_RE.search(url) or _ANY_NUM.search(url)
        if not m:
            raise ScraperError(
                "Не удалось распознать товар Яндекс.Маркета. Нужна ссылка вида "
                "market.yandex.ru/product--nazvanie/123456789"
            )
        return m.group(1)

    def _target_url(self, url: str) -> str:
        base = url.split("?")[0].rstrip("/")
        return f"{base}/reviews"

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
                rid = str(raw.get("id") or raw.get("entityId") or len(reviews))
                if rid in reviews:
                    continue
                mapped = _map(rid, raw)
                if mapped:
                    reviews[rid] = mapped
        return ScrapeResult(product=product, reviews=list(reviews.values()))


def _title(html: str) -> str | None:
    m = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return m.group(1).split(" — ")[0].strip() if m else None


def _map(rid: str, raw: dict) -> ScrapedReview | None:
    text = raw.get("text") or raw.get("comment")
    pros = raw.get("pro") or raw.get("pros") or raw.get("advantages")
    cons = raw.get("contra") or raw.get("cons") or raw.get("disadvantages")
    if not (text or pros or cons):
        return None
    grade = raw.get("grade") or raw.get("rating")
    date = None
    raw_date = raw.get("created") or raw.get("date") or raw.get("updatedAt")
    if raw_date:
        try:
            date = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            date = None
    return ScrapedReview(
        external_id=rid,
        rating=int(grade) if isinstance(grade, (int, float)) else None,
        text=text or None,
        pros=pros if isinstance(pros, str) else None,
        cons=cons if isinstance(cons, str) else None,
        review_date=date,
    )
