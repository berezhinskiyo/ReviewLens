import os

import pytest

from app.scrapers.base import ScraperError
from app.scrapers.registry import detect_marketplace
from app.scrapers.wildberries import WildberriesScraper


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.wildberries.ru/catalog/12345678/detail.aspx", "12345678"),
        ("https://www.wildberries.ru/catalog/199001/detail.aspx?targetUrl=GP", "199001"),
        ("wildberries.ru/catalog/55555555/detail.aspx", "55555555"),
    ],
)
def test_parse_url(url: str, expected: str) -> None:
    assert WildberriesScraper().parse_url(url) == expected


def test_parse_url_invalid() -> None:
    with pytest.raises(ScraperError):
        WildberriesScraper().parse_url("https://example.com/no-article")


def test_detect_marketplace() -> None:
    assert detect_marketplace("https://www.wildberries.ru/catalog/1/detail.aspx") == "wb"
    assert detect_marketplace("https://www.ozon.ru/product/abc-1") == "ozon"
    with pytest.raises(ScraperError):
        detect_marketplace("https://aliexpress.com/item/1")


# Живые артикулы WB — запускать осознанно: RUN_LIVE_SCRAPER=1 pytest -k live
LIVE_ARTICLES = ["199001", "12345678"]


@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_SCRAPER"), reason="живой парсинг WB, нужен RUN_LIVE_SCRAPER=1"
)
@pytest.mark.parametrize("article", LIVE_ARTICLES)
async def test_live_scrape(article: str) -> None:
    url = f"https://www.wildberries.ru/catalog/{article}/detail.aspx"
    async with WildberriesScraper() as scraper:
        result = await scraper.scrape(url, max_reviews=50)
    assert result.product.external_id == article
    assert len(result.reviews) > 0
