from app.scrapers.base import BaseScraper, ScraperError
from app.scrapers.ozon import OzonScraper
from app.scrapers.wildberries import WildberriesScraper


def detect_marketplace(url: str) -> str:
    low = url.lower()
    if "wildberries.ru" in low or "wb.ru" in low:
        return "wb"
    if "ozon.ru" in low:
        return "ozon"
    raise ScraperError(
        "Не удалось определить маркетплейс. Поддерживается ссылка на Wildberries."
    )


def get_scraper(marketplace: str) -> BaseScraper:
    if marketplace == "wb":
        return WildberriesScraper()
    if marketplace == "ozon":
        return OzonScraper()
    raise ScraperError(f"Неизвестный маркетплейс: {marketplace}")
