from app.scrapers.base import BaseScraper, ScrapeResult, ScraperError


class OzonScraper(BaseScraper):
    """Ozon в MVP не поддерживается (см. ТЗ 7.2).

    Требует headless-браузер / внутренний API через сессию — вынесено в BACKLOG.
    Кнопка Ozon в UI помечена «скоро» и disabled.
    """

    marketplace = "ozon"

    def parse_url(self, url: str) -> str:  # noqa: ARG002
        raise ScraperError("Поддержка Ozon появится позже. Пока доступен только Wildberries.")

    async def scrape(self, url: str, max_reviews: int) -> ScrapeResult:  # noqa: ARG002
        raise ScraperError("Поддержка Ozon появится позже. Пока доступен только Wildberries.")
