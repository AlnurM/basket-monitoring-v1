import logging
import re

import httpx
from selectolax.parser import HTMLParser

from .base import BaseScraper
from .models import PriceResult
from .stealth import random_ua

logger = logging.getLogger(__name__)

KASPI_URL_PATTERN = re.compile(
    r"https?://kaspi\.kz/shop/p/[\w-]+-(\d+)"
)


class KaspiScraper(BaseScraper):
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                http2=True,
            )
        return self._client

    async def scrape(self, url: str) -> PriceResult:
        client = await self._get_client()
        resp = await client.get(
            url,
            headers={
                "User-Agent": random_ua(),
                "Accept-Language": "ru-KZ,ru;q=0.9",
            },
        )
        resp.raise_for_status()

        tree = HTMLParser(resp.text)

        name = self._extract_name(tree)
        price = self._extract_price(tree)
        original_price = self._extract_original_price(tree)
        is_available = self._check_availability(tree)

        return PriceResult(
            name=name,
            price=price,
            original_price=original_price,
            is_available=is_available,
        )

    def _extract_name(self, tree: HTMLParser) -> str:
        # Try h1 first, then meta og:title
        h1 = tree.css_first("h1")
        if h1 and h1.text(strip=True):
            return h1.text(strip=True)
        og = tree.css_first('meta[property="og:title"]')
        if og:
            content = og.attributes.get("content", "")
            if content:
                return content.strip()
        raise ValueError("Kaspi: could not find product name")

    def _extract_price(self, tree: HTMLParser) -> int:
        # Try structured data / meta tags first
        for selector in [
            'meta[itemprop="price"]',
            '[itemprop="price"]',
            ".item__price-once",
            ".item__price",
            '[class*="price"]',
        ]:
            node = tree.css_first(selector)
            if node:
                text = node.attributes.get("content", "") or node.text(
                    strip=True
                )
                price = self._parse_price_text(text)
                if price:
                    return price
        raise ValueError("Kaspi: could not find price")

    def _extract_original_price(self, tree: HTMLParser) -> int | None:
        for selector in [
            ".item__price-old",
            "[class*='price'] del",
            "[class*='old-price']",
        ]:
            node = tree.css_first(selector)
            if node:
                text = node.text(strip=True)
                price = self._parse_price_text(text)
                if price:
                    return price
        return None

    def _check_availability(self, tree: HTMLParser) -> bool:
        # If there is an add-to-cart button or buy button, product is available
        buy_btn = tree.css_first(
            '[class*="buy"], [class*="cart"], button[class*="add"]'
        )
        if buy_btn:
            return True
        # Check for "not available" text
        body_text = tree.body.text() if tree.body else ""
        if (
            "нет в наличии" in body_text.lower()
            or "not available" in body_text.lower()
        ):
            return False
        return True  # Assume available if no negative signal

    @staticmethod
    def _parse_price_text(text: str) -> int | None:
        digits = re.sub(r"[^\d]", "", text)
        return int(digits) if digits else None

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
