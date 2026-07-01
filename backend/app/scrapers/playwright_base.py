"""База для скраперов на headless-браузере (Ozon / Яндекс.Маркет / Avito).

Подход устойчив к смене вёрстки: мы не парсим CSS-селекторы, а перехватываем
JSON-ответы, которые сама страница грузит для отзывов (XHR/fetch), и разбираем
их. Требует установленного Playwright + Chromium (см. Dockerfile.playwright).
"""

import asyncio
import json
from dataclasses import dataclass, field

from app.core.logging import logger
from app.scrapers.base import BaseScraper, ScrapeResult, ScraperError


@dataclass
class CapturedResponse:
    url: str
    json: object | None = None


@dataclass
class PageCapture:
    html: str = ""
    responses: list[CapturedResponse] = field(default_factory=list)
    # Текст отзывов, вытащенный прямо из DOM (фолбэк, если XHR пустой)
    dom_texts: list[str] = field(default_factory=list)

    def matching(self, *needles: str) -> list[object]:
        out = []
        for r in self.responses:
            if r.json is not None and any(n in r.url for n in needles):
                out.append(r.json)
        return out


class PlaywrightScraper(BaseScraper):
    """Навигация по карточке + перехват сетевых JSON-ответов с отзывами."""

    marketplace = ""
    # Подстроки URL XHR-запросов, которые нас интересуют (переопределяется)
    CAPTURE_URL_NEEDLES: tuple[str, ...] = ()
    # CSS-селектор контейнеров отзывов для DOM-фолбэка (переопределяется)
    DOM_REVIEW_SELECTOR: str = "[data-review-uuid], [class*='review' i], article"
    # Блокировать картинки/медиа/шрифты/стили (экономит трафик медленного прокси)
    BLOCK_RESOURCES = True
    SCROLLS = 8
    SCROLL_PAUSE_MS = 1500
    NAV_TIMEOUT_MS = 60000

    async def __aexit__(self, *exc: object) -> None:
        # httpx-клиент базового класса нам не нужен, но закроем его
        await super().__aexit__(*exc)

    async def _capture(self, url: str) -> PageCapture:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:  # pragma: no cover
            raise ScraperError(
                f"Для {self.marketplace} нужен headless-браузер. Установите "
                "playwright и Chromium (см. Dockerfile.playwright)."
            ) from exc

        from app.core.config import settings

        launch_kwargs: dict = {
            "headless": True,
            "args": ["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        }
        if settings.scraper_proxy:
            launch_kwargs["proxy"] = {"server": settings.scraper_proxy}

        capture = PageCapture()
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(**launch_kwargs)
            context = await browser.new_context(
                locale="ru-RU",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1366, "height": 900},
            )

            async def on_response(resp) -> None:
                u = resp.url
                if not any(n in u for n in self.CAPTURE_URL_NEEDLES):
                    return
                try:
                    body = await resp.body()
                    capture.responses.append(
                        CapturedResponse(url=u, json=json.loads(body))
                    )
                except Exception:  # noqa: BLE001 — не JSON / гонка — пропускаем
                    pass

            # Блокируем тяжёлые ресурсы (картинки/медиа/шрифты/стили) — они не нужны
            # для текста отзывов, но съедают весь трафик медленного прокси.
            if self.BLOCK_RESOURCES:
                blocked = {"image", "media", "font", "stylesheet"}

                async def _router(route) -> None:
                    if route.request.resource_type in blocked:
                        await route.abort()
                    else:
                        await route.continue_()

                await context.route("**/*", _router)

            context.on("response", on_response)
            page = await context.new_page()
            try:
                await page.goto(url, timeout=self.NAV_TIMEOUT_MS, wait_until="commit")
                # Прокрутка, чтобы догрузить отзывы (ленивые XHR)
                for _ in range(self.SCROLLS):
                    await page.mouse.wheel(0, 2500)
                    await page.wait_for_timeout(self.SCROLL_PAUSE_MS)
                capture.html = await page.content()
                # DOM-фолбэк: собираем текст из контейнеров отзывов
                try:
                    capture.dom_texts = await page.eval_on_selector_all(
                        self.DOM_REVIEW_SELECTOR,
                        "els => els.map(e => e.innerText)"
                        ".filter(t => t && t.trim().length > 40)",
                    )
                except Exception:  # noqa: BLE001
                    capture.dom_texts = []
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "playwright.nav_failed", marketplace=self.marketplace, error=str(exc)
                )
            finally:
                await context.close()
                await browser.close()

        return capture

    def parse_url(self, url: str) -> str:
        raise NotImplementedError

    def _target_url(self, url: str) -> str:
        """Страница для открытия (по умолчанию — исходная карточка)."""
        return url

    def parse_capture(self, external_id: str, url: str, cap: PageCapture) -> ScrapeResult:
        raise NotImplementedError

    # Жёсткий общий таймаут на браузерный сбор — чтобы воркер не висел на
    # медленном прокси (иначе задача держится до RQ-таймаута в 10 минут).
    OVERALL_TIMEOUT_S = 150

    async def scrape(self, url: str, max_reviews: int) -> ScrapeResult:
        external_id = self.parse_url(url)
        logger.info("pw.scrape.start", marketplace=self.marketplace, id=external_id)
        try:
            cap = await asyncio.wait_for(
                self._capture(self._target_url(url)), timeout=self.OVERALL_TIMEOUT_S
            )
        except asyncio.TimeoutError as exc:
            raise ScraperError(
                "Площадка не ответила вовремя (вероятно, медленный прокси/анти-бот). "
                "Нужен более быстрый резидентный прокси или платный парсинг-API."
            ) from exc
        result = self.parse_capture(external_id, url, cap)
        # Фолбэк: если из XHR отзывы не разобрались, берём тексты из DOM
        if not result.reviews and cap.dom_texts:
            from app.scrapers.base import ScrapedReview

            result.reviews = [
                ScrapedReview(external_id=str(i), text=t.strip())
                for i, t in enumerate(cap.dom_texts)
            ]
        result.reviews = result.reviews[:max_reviews]
        if not result.reviews:
            raise ScraperError(
                "Не удалось получить отзывы. Возможна анти-бот защита — на проде "
                "может потребоваться прокси."
            )
        logger.info(
            "pw.scrape.done", marketplace=self.marketplace, reviews=len(result.reviews)
        )
        return result


def deep_find_lists(obj: object, key_hints: tuple[str, ...]) -> list[dict]:
    """Рекурсивно ищет в JSON списки словарей, похожих на отзывы (по ключам)."""
    found: list[dict] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            dicts = [x for x in node if isinstance(x, dict)]
            if dicts and any(
                any(h in (k.lower()) for k in d.keys() for h in key_hints)
                for d in dicts[:3]
            ):
                found.extend(dicts)
            for v in node:
                walk(v)

    walk(obj)
    return found
