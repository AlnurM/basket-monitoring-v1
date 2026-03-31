"""Kaspi.kz scraper — uses Playwright since prices load via JavaScript."""

import logging
import re

from playwright.async_api import Page, Response

from price_spy.config import settings

from .base import BaseScraper
from .browser import browser_manager
from .models import PriceResult
from .stealth import apply_stealth

logger = logging.getLogger(__name__)

KASPI_URL_PATTERN = re.compile(
    r"https?://kaspi\.kz/shop/p/[\w-]+-(\d+)"
)

# Selectors verified from live Kaspi.kz inspection (2026-03-31)
PRICE_SELECTORS = [
    ".item__price-once",
    ".item__price",
    '[class*="price"]',
]
NAME_SELECTORS = [
    "h1",
    'meta[property="og:title"]',
]


class KaspiScraper(BaseScraper):
    async def scrape(self, url: str) -> PriceResult:
        api_data: dict = {}

        async def capture_response(response: Response) -> None:
            """Capture the offers API response for structured price data."""
            try:
                resp_url = response.url
                if "yml/offer-view/offers" in resp_url and response.status == 200:
                    body = await response.json()
                    api_data["offers"] = body
                    logger.debug("Kaspi API intercept: captured offers from %s", resp_url)
            except Exception:
                pass

        async with browser_manager.new_context() as ctx:
            page = await ctx.new_page()
            await apply_stealth(page)
            page.on("response", capture_response)

            await page.goto(
                url, wait_until="networkidle", timeout=settings.scrape_timeout
            )

            # Try API data first (offers endpoint)
            if api_data.get("offers"):
                result = self._parse_offers_api(api_data["offers"])
                if result:
                    logger.info("Kaspi: used API interception for %s", url)
                    return result

            # Fallback: DOM extraction
            logger.info("Kaspi: falling back to DOM extraction for %s", url)
            return await self._extract_from_dom(page)

    def _parse_offers_api(self, data: dict | list) -> PriceResult | None:
        """Parse the Kaspi offers API response."""
        try:
            offers = data if isinstance(data, list) else data.get("offers", [])
            if not offers:
                return None

            # Take the first (cheapest) offer
            offer = offers[0]
            price = offer.get("price")
            name = offer.get("title") or offer.get("productName")
            if price and name:
                return PriceResult(
                    name=str(name),
                    price=int(float(str(price))),
                    original_price=None,
                    is_available=True,
                )
        except (ValueError, TypeError, KeyError, IndexError) as e:
            logger.debug("Kaspi offers API parse failed: %s", e)
        return None

    async def _extract_from_dom(self, page: Page) -> PriceResult:
        """Extract price data from rendered DOM."""
        # Name from h1
        name = None
        h1 = page.locator("h1").first
        if await h1.count() > 0:
            text = await h1.text_content()
            if text and text.strip():
                name = text.strip()
        if not name:
            raise ValueError("Kaspi: could not find product name on page")

        # Price from .item__price-once
        price_text = None
        for sel in PRICE_SELECTORS:
            loc = page.locator(sel).first
            try:
                if await loc.count() > 0:
                    text = await loc.text_content()
                    if text and text.strip():
                        price_text = text.strip()
                        break
            except Exception:
                continue
        if not price_text:
            raise ValueError("Kaspi: could not find price on page")

        # Check availability
        sellers = await page.locator(".sellers__header").count()
        is_available = sellers > 0

        return PriceResult(
            name=name,
            price=self._parse_price(price_text),
            original_price=None,
            is_available=is_available,
        )

    @staticmethod
    def _parse_price(text: str) -> int:
        """Extract integer price from text like '1 050 ₸'."""
        digits = re.sub(r"[^\d]", "", text)
        if not digits:
            raise ValueError(f"Cannot parse price from: {text}")
        return int(digits)

    async def close(self) -> None:
        pass  # Browser lifecycle managed by BrowserManager
