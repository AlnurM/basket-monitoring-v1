import logging
import re

from playwright.async_api import BrowserContext, Page, Response

from price_spy.config import settings

from .base import BaseScraper
from .browser import browser_manager
from .models import PriceResult
from .stealth import apply_stealth

logger = logging.getLogger(__name__)

# URL pattern from task.md section 6.4
ARBUZ_URL_PATTERN = re.compile(
    r"https?://arbuz\.kz/ru/\w+/catalog/item/(\d+)-[\w-]+"
)

# Multi-selector fallback lists (refined from live Arbuz.kz inspection 2026-03-31)
PRICE_SELECTORS = [
    ".product-card-price-actual",
    ".product-price",
    '[data-testid="price"]',
    ".price-current",
    '[class*="price"] [class*="current"]',
]
ORIGINAL_PRICE_SELECTORS = [
    ".product-card-old-price",
    ".old-price",
    ".crossed-price",
    '[class*="price"] [class*="old"]',
    "del",
]
NAME_SELECTORS = [
    "h1",
    ".product-title",
    '[data-testid="product-name"]',
]


class ArbuzScraper(BaseScraper):
    async def scrape(self, url: str) -> PriceResult:
        api_data: dict = {}

        async def capture_response(response: Response) -> None:
            """Capture JSON API responses during page load (D-01 API interception)."""
            try:
                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type and response.status == 200:
                    body = await response.json()
                    body_str = str(body).lower()
                    if "price" in body_str and (
                        "name" in body_str or "title" in body_str
                    ):
                        api_data["response"] = body
                        logger.debug(
                            "Arbuz API intercept: captured JSON from %s",
                            response.url,
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
                    logger.info("Arbuz: used API interception for %s", url)
                    return result

            # Fallback: DOM extraction
            logger.info("Arbuz: falling back to DOM extraction for %s", url)
            return await self._extract_from_dom(page)

    def _parse_api_response(self, data: dict) -> PriceResult | None:
        """Attempt to extract price data from intercepted JSON.

        Returns None if structure unrecognized.
        """
        try:
            # Structure is unknown until live testing -- try common patterns
            for container_key in ["data", "product", "item", "result"]:
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
                        op = container.get("original_price") or container.get(
                            "old_price"
                        )
                        return PriceResult(
                            name=str(name),
                            price=int(float(str(price))),
                            original_price=int(float(str(op))) if op else None,
                            is_available=(
                                container.get("is_available", True)
                                if "is_available" in container
                                else container.get("in_stock", True)
                            ),
                        )
        except (ValueError, TypeError, KeyError) as e:
            logger.debug("Arbuz API parse failed: %s", e)
        return None

    async def _extract_from_dom(self, page: Page) -> PriceResult:
        """Extract price data from page DOM using multi-selector fallback (D-02)."""
        name = await self._try_selectors(page, NAME_SELECTORS)
        if not name:
            raise ValueError("Arbuz: could not find product name on page")

        price_text = await self._try_selectors(page, PRICE_SELECTORS)
        if not price_text:
            raise ValueError("Arbuz: could not find price on page")

        original_price_text = await self._try_selectors(
            page, ORIGINAL_PRICE_SELECTORS
        )

        # Check availability: if "add to cart" or similar button exists
        is_available = (
            await page.locator(
                'button:has-text("В корзину"), '
                'button:has-text("Добавить"), '
                '[data-testid="add-to-cart"]'
            ).count()
            > 0
        )

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
