import json
import logging
import re

from playwright.async_api import Page, Response

from price_spy.config import settings

from .base import BaseScraper
from .browser import browser_manager
from .models import PriceResult
from .stealth import apply_stealth

logger = logging.getLogger(__name__)

# URL pattern for Magnum
MAGNUM_URL_PATTERN = re.compile(r"https?://magnum\.kz/products/(\d+)")

# Multi-selector fallback lists (D-02: will be refined during live testing)
PRICE_SELECTORS = [
    '[data-testid="price"]',
    ".product-price",
    ".price-current",
    '[class*="price"] [class*="current"]',
    ".product-block__price",
    ".item-price",
]
ORIGINAL_PRICE_SELECTORS = [
    ".old-price",
    ".crossed-price",
    '[class*="price"] [class*="old"]',
    '[class*="price"] s',
    "del",
]
NAME_SELECTORS = [
    "h1",
    ".product-title",
    '[data-testid="product-name"]',
    ".product-block__title",
    ".item-title",
]


class MagnumScraper(BaseScraper):
    async def scrape(self, url: str) -> PriceResult:
        api_data: dict = {}

        async def capture_response(response: Response) -> None:
            """Capture JSON API responses during page load (D-01 API interception).

            Also watches for Next.js _next/data responses.
            """
            try:
                resp_url = response.url
                content_type = response.headers.get("content-type", "")

                # Check _next/data endpoints (Next.js SPA data routes)
                is_next_data = "/_next/data/" in resp_url
                is_json = "application/json" in content_type

                if (is_json or is_next_data) and response.status == 200:
                    body = await response.json()
                    body_str = str(body).lower()
                    if "price" in body_str and (
                        "name" in body_str or "title" in body_str
                    ):
                        api_data["response"] = body
                        logger.debug(
                            "Magnum API intercept: captured JSON from %s",
                            resp_url,
                        )
            except Exception:
                pass

        async with browser_manager.new_context() as ctx:
            page = await ctx.new_page()
            await apply_stealth(page)
            page.on("response", capture_response)

            await page.goto(
                url, wait_until="networkidle", timeout=settings.scrape_timeout
            )

            # Try API data first
            if api_data.get("response"):
                result = self._parse_api_response(api_data["response"])
                if result:
                    logger.info("Magnum: used API interception for %s", url)
                    return result

            # Mid-tier fallback: try __NEXT_DATA__ script tag
            next_data_result = await self._extract_next_data(page)
            if next_data_result:
                logger.info(
                    "Magnum: used __NEXT_DATA__ extraction for %s", url
                )
                return next_data_result

            # Final fallback: DOM extraction
            logger.info("Magnum: falling back to DOM extraction for %s", url)
            return await self._extract_from_dom(page)

    def _parse_api_response(self, data: dict) -> PriceResult | None:
        """Attempt to extract price data from intercepted JSON.

        Returns None if structure unrecognized.
        """
        try:
            # Handle Next.js pageProps wrapper
            if "pageProps" in data:
                data = data["pageProps"]

            for container_key in [
                "data",
                "product",
                "item",
                "result",
                "props",
            ]:
                container = data.get(container_key, data)
                if isinstance(container, dict):
                    price = (
                        container.get("price")
                        or container.get("current_price")
                        or container.get("sell_price")
                    )
                    name = (
                        container.get("name")
                        or container.get("title")
                        or container.get("product_name")
                    )
                    if price and name:
                        op = container.get(
                            "original_price"
                        ) or container.get("old_price")
                        return PriceResult(
                            name=str(name),
                            price=int(float(str(price))),
                            original_price=(
                                int(float(str(op))) if op else None
                            ),
                            is_available=(
                                container.get("is_available", True)
                                if "is_available" in container
                                else container.get("in_stock", True)
                            ),
                        )
        except (ValueError, TypeError, KeyError) as e:
            logger.debug("Magnum API parse failed: %s", e)
        return None

    async def _extract_next_data(self, page: Page) -> PriceResult | None:
        """Try to extract product data from Next.js __NEXT_DATA__ script tag."""
        try:
            script = page.locator('script#__NEXT_DATA__')
            if await script.count() > 0:
                raw = await script.text_content()
                if raw:
                    data = json.loads(raw)
                    props = data.get("props", {}).get("pageProps", {})
                    return self._parse_api_response(props)
        except Exception as e:
            logger.debug("Magnum __NEXT_DATA__ extraction failed: %s", e)
        return None

    async def _extract_from_dom(self, page: Page) -> PriceResult:
        """Extract price data from page DOM using multi-selector fallback (D-02)."""
        name = await self._try_selectors(page, NAME_SELECTORS)
        if not name:
            raise ValueError("Magnum: could not find product name on page")

        price_text = await self._try_selectors(page, PRICE_SELECTORS)
        if not price_text:
            raise ValueError("Magnum: could not find price on page")

        original_price_text = await self._try_selectors(
            page, ORIGINAL_PRICE_SELECTORS
        )

        # Availability: check absence of "not available" indicators
        not_available_text = await page.locator(
            'text="Нет в наличии", text="Временно недоступен"'
        ).count()
        is_available = not_available_text == 0

        return PriceResult(
            name=name,
            price=self._parse_price(price_text),
            original_price=(
                self._parse_price(original_price_text)
                if original_price_text
                else None
            ),
            is_available=is_available,
        )

    async def _try_selectors(
        self, page: Page, selectors: list[str]
    ) -> str | None:
        """Try each selector in order, return text content of first match."""
        for selector in selectors:
            try:
                loc = page.locator(selector).first
                if await loc.count() > 0:
                    text = await loc.text_content()
                    if text and text.strip():
                        return text.strip()
            except Exception:
                continue
        return None

    @staticmethod
    def _parse_price(text: str) -> int:
        """Extract integer price from text like '1 890 T' or '1890'."""
        digits = re.sub(r"[^\d]", "", text)
        if not digits:
            raise ValueError(f"Cannot parse price from: {text}")
        return int(digits)

    async def close(self) -> None:
        pass  # Browser lifecycle managed by BrowserManager
