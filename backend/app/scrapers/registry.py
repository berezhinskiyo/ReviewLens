from app.scrapers.base import BaseScraper, ScraperError

# Поддерживаемые маркетплейсы и распознавание по домену
_MARKET_DOMAINS = {
    "wb": ("wildberries.ru", "wb.ru"),
    "ozon": ("ozon.ru",),
    "yandex": ("market.yandex.ru",),
    "megamarket": ("megamarket.ru", "sbermegamarket.ru"),
    "avito": ("avito.ru",),
}

MARKET_TITLES = {
    "wb": "Wildberries",
    "ozon": "Ozon",
    "yandex": "Яндекс.Маркет",
    "megamarket": "Мегамаркет",
    "avito": "Avito",
}


def detect_marketplace(url: str) -> str:
    low = url.lower()
    for code, domains in _MARKET_DOMAINS.items():
        if any(d in low for d in domains):
            return code
    raise ScraperError(
        "Не удалось определить маркетплейс. Поддерживаются ссылки на "
        "Wildberries, Ozon, Яндекс.Маркет, Мегамаркет и Avito."
    )


def get_scraper(marketplace: str) -> BaseScraper:
    # Ленивые импорты: тяжёлый Playwright тянем только для нужных площадок.
    if marketplace == "wb":
        from app.scrapers.wildberries import WildberriesScraper

        return WildberriesScraper()
    if marketplace == "megamarket":
        from app.scrapers.megamarket import MegamarketScraper

        return MegamarketScraper()
    if marketplace == "ozon":
        from app.scrapers.ozon import OzonScraper

        return OzonScraper()
    if marketplace == "yandex":
        from app.scrapers.yandex import YandexMarketScraper

        return YandexMarketScraper()
    if marketplace == "avito":
        from app.scrapers.avito import AvitoScraper

        return AvitoScraper()
    raise ScraperError(f"Неизвестный маркетплейс: {marketplace}")
