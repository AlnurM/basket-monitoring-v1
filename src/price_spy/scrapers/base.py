from abc import ABC, abstractmethod

from .models import PriceResult


class BaseScraper(ABC):
    @abstractmethod
    async def scrape(self, url: str) -> PriceResult:
        """Scrape a product URL and return validated price data."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Release any resources."""
        ...
