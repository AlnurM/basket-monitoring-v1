"""Daily scrape orchestration service.

Provides scrape_all_baskets() for the scheduled daily job and
scrape_single_basket() for the /scrape command handler.
Both manage their own database sessions (they run outside middleware).
"""

import logging
from decimal import Decimal

from price_spy.db.engine import async_session
from price_spy.db.repositories.basket import BasketRepository
from price_spy.db.repositories.basket_item import BasketItemRepository
from price_spy.db.repositories.price_history import PriceHistoryRepository
from price_spy.services.scraper import ScrapeResult, ScraperService

logger = logging.getLogger(__name__)


async def scrape_all_baskets() -> dict[int, list[ScrapeResult]]:
    """Scrape all baskets across all users with URL deduplication.

    Returns dict mapping basket_id to list of ScrapeResult for that basket's items.
    """
    async with async_session() as session:
        basket_repo = BasketRepository(session)
        item_repo = BasketItemRepository(session)
        price_repo = PriceHistoryRepository(session)

        baskets = await basket_repo.get_all_active_baskets()
        if not baskets:
            logger.info("No baskets to scrape")
            return {}

        # Build deduplication maps
        # url -> list of basket_item_ids that share this URL
        url_to_item_ids: dict[str, list[int]] = {}
        # basket_item_id -> basket_id
        item_to_basket: dict[int, int] = {}
        # basket_item_id -> BasketItem (for name updates)
        item_map: dict[int, object] = {}

        for basket in baskets:
            items = await item_repo.get_items_by_basket(basket.id)
            for item in items:
                url_to_item_ids.setdefault(item.product_url, []).append(item.id)
                item_to_basket[item.id] = basket.id
                item_map[item.id] = item

        if not url_to_item_ids:
            logger.info("No items across all baskets")
            return {}

        unique_urls = list(url_to_item_ids.keys())
        logger.info(
            "Scraping %d unique URLs across %d baskets",
            len(unique_urls),
            len(baskets),
        )

        # Scrape all unique URLs
        scraper = ScraperService(session)
        try:
            results = await scraper.scrape_urls(unique_urls)
        finally:
            await scraper.close()

        # Build URL -> ScrapeResult map
        url_to_result: dict[str, ScrapeResult] = {r.url: r for r in results}

        # Store PriceHistory for each basket_item and build per-basket results
        basket_results: dict[int, list[ScrapeResult]] = {}

        for url, item_ids in url_to_item_ids.items():
            result = url_to_result.get(url)
            if result is None:
                continue

            for item_id in item_ids:
                basket_id = item_to_basket[item_id]
                basket_results.setdefault(basket_id, []).append(result)

                if result.ok and result.data is not None:
                    await price_repo.create(
                        basket_item_id=item_id,
                        price=Decimal(result.data.price),
                        original_price=(
                            Decimal(result.data.original_price)
                            if result.data.original_price is not None
                            else None
                        ),
                        is_available=result.data.is_available,
                    )

                    # Update item name if it was None (product name caching)
                    item = item_map.get(item_id)
                    if (
                        item is not None
                        and getattr(item, "name", None) is None
                        and result.data.name
                    ):
                        await item_repo.update_name(item_id, result.data.name)

        await session.commit()

        success_count = sum(1 for r in results if r.ok)
        logger.info(
            "Scrape complete: %d/%d URLs successful",
            success_count,
            len(results),
        )
        return basket_results


async def scrape_single_basket(basket_id: int) -> list[ScrapeResult]:
    """Scrape a single basket (for /scrape command).

    Returns list of ScrapeResult for the basket's items.
    """
    async with async_session() as session:
        item_repo = BasketItemRepository(session)
        price_repo = PriceHistoryRepository(session)

        items = await item_repo.get_items_by_basket(basket_id)
        if not items:
            logger.info("No items in basket %d", basket_id)
            return []

        urls = [item.product_url for item in items]
        url_to_item = {item.product_url: item for item in items}

        scraper = ScraperService(session)
        try:
            results = await scraper.scrape_urls(urls)
        finally:
            await scraper.close()

        for result in results:
            if result.ok and result.data is not None:
                item = url_to_item.get(result.url)
                if item is None:
                    continue

                await price_repo.create(
                    basket_item_id=item.id,
                    price=Decimal(result.data.price),
                    original_price=(
                        Decimal(result.data.original_price)
                        if result.data.original_price is not None
                        else None
                    ),
                    is_available=result.data.is_available,
                )

                # Update item name if it was None
                if item.name is None and result.data.name:
                    await item_repo.update_name(item.id, result.data.name)

        await session.commit()
        return results
