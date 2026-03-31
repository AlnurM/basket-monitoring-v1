import asyncio
import logging
import random
import re
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from price_spy.config import settings
from price_spy.db.repositories.product_cache import ProductCacheRepository
from price_spy.scrapers.arbuz import ArbuzScraper
from price_spy.scrapers.base import BaseScraper
from price_spy.scrapers.kaspi import KaspiScraper
from price_spy.scrapers.magnum import MagnumScraper
from price_spy.scrapers.models import PriceResult

logger = logging.getLogger(__name__)

# URL routing patterns from task.md section 6.4
URL_PATTERNS = {
    "arbuz": re.compile(r"https?://arbuz\.kz/ru/\w+/catalog/item/(\d+)-[\w-]+"),
    "magnum": re.compile(r"https?://magnum\.kz/products/(\d+)"),
    "kaspi": re.compile(r"https?://kaspi\.kz/shop/p/[\w-]+-(\d+)"),
}

SOURCE_TO_BASKET = {
    "arbuz": "arbuz",
    "magnum": "magnum",
    "kaspi": "magnum",
}


@dataclass
class ScrapeResult:
    """Result of a single scrape attempt. Either success with data or failure with error."""

    url: str
    source: str
    data: PriceResult | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.data is not None


def detect_source(url: str) -> str | None:
    """Detect which store a URL belongs to. Returns 'arbuz', 'magnum', 'kaspi', or None."""
    for source, pattern in URL_PATTERNS.items():
        if pattern.match(url):
            return source
    return None


def extract_product_id(url: str, source: str) -> str | None:
    """Extract product ID from URL given its source."""
    pattern = URL_PATTERNS.get(source)
    if pattern:
        m = pattern.match(url)
        if m:
            return m.group(1)
    return None


class ScraperService:
    """Orchestrates scraping with concurrency control, retries, and name caching (SCRP-05)."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session
        self._cache = ProductCacheRepository(session) if session else None
        self._playwright_semaphore = asyncio.Semaphore(
            settings.scrape_concurrency
        )  # max 3 per SCRP-09
        self._httpx_semaphore = asyncio.Semaphore(10)  # max 10 per SCRP-09
        self._scrapers: dict[str, BaseScraper] = {
            "arbuz": ArbuzScraper(),
            "magnum": MagnumScraper(),
            "kaspi": KaspiScraper(),
        }

    async def scrape_urls(self, urls: list[str]) -> list[ScrapeResult]:
        """Scrape multiple URLs in parallel with appropriate concurrency limits."""
        tasks = [self._scrape_single(url) for url in urls]
        return await asyncio.gather(*tasks)

    async def _scrape_single(self, url: str) -> ScrapeResult:
        """Scrape a single URL with retry (D-08: silent retries, report only final failure)."""
        source = detect_source(url)
        if not source:
            return ScrapeResult(
                url=url,
                source="unknown",
                error=f"Unrecognized URL format: {url}",
            )

        semaphore = (
            self._httpx_semaphore
            if source == "kaspi"
            else self._playwright_semaphore
        )
        scraper = self._scrapers[source]

        # SCRP-05: Check name cache before scraping
        cached_name: str | None = None
        if self._cache:
            cached_name = await self._cache.get_name(url)

        last_error: Exception | None = None
        for attempt in range(settings.scrape_retry_count):
            try:
                async with semaphore:
                    data = await scraper.scrape(url)
                # SCRP-05: Use cached name if available; cache new name if not
                if cached_name:
                    data.name = cached_name
                elif data.name and self._cache:
                    pid = extract_product_id(url, source) or ""
                    await self._cache.set_name(url, source, pid, data.name)
                return ScrapeResult(url=url, source=source, data=data)
            except Exception as e:
                last_error = e
                if attempt < settings.scrape_retry_count - 1:
                    delay = (2**attempt) + random.uniform(0, 1)
                    logger.warning(
                        "Scrape attempt %d/%d failed for %s: %s. Retrying in %.1fs",
                        attempt + 1,
                        settings.scrape_retry_count,
                        url,
                        e,
                        delay,
                    )
                    await asyncio.sleep(delay)

        # D-07: detailed diagnostic error per D-09: individual per item
        error_msg = (
            f"timeout after {settings.scrape_timeout}ms on {source}"
            if "timeout" in str(last_error).lower()
            else str(last_error)
        )
        logger.error(
            "Scrape failed for %s after %d attempts: %s",
            url,
            settings.scrape_retry_count,
            error_msg,
        )
        return ScrapeResult(url=url, source=source, error=error_msg)

    async def close(self) -> None:
        """Close all scraper resources."""
        for scraper in self._scrapers.values():
            await scraper.close()
