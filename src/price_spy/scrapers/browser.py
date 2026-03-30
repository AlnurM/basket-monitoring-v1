import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

from .stealth import random_ua, random_viewport

logger = logging.getLogger(__name__)

CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--disable-setuid-sandbox",
    "--single-process",
]


class BrowserManager:
    """Singleton browser manager. One Chromium instance, fresh contexts per scrape batch."""

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._page_count: int = 0
        self._max_pages_before_recycle: int = 100

    async def start(self) -> None:
        """Launch Playwright and Chromium. Call once at application startup."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=CHROMIUM_ARGS,
        )
        self._page_count = 0
        logger.info("BrowserManager: Chromium launched")

    async def close(self) -> None:
        """Shut down browser and Playwright. Call at application shutdown."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("BrowserManager: shut down")

    @asynccontextmanager
    async def new_context(self) -> AsyncIterator[BrowserContext]:
        """Create a fresh browser context with randomized fingerprint. Always close after use."""
        if self._browser is None:
            raise RuntimeError("BrowserManager not started. Call start() first.")

        # Recycle browser if page count exceeded
        if self._page_count >= self._max_pages_before_recycle:
            logger.info("BrowserManager: recycling browser after %d pages", self._page_count)
            await self.close()
            await self.start()

        viewport = random_viewport()
        ctx = await self._browser.new_context(
            user_agent=random_ua(),
            viewport=viewport,
            locale="ru-KZ",
            timezone_id="Asia/Almaty",
        )
        try:
            yield ctx
        finally:
            self._page_count += 1
            await ctx.close()


# Module-level singleton, initialized via start() during app startup
browser_manager = BrowserManager()
