from decimal import Decimal

from sqlalchemy import delete, func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from price_spy.db.models.basket_item import BasketItem
from price_spy.db.models.price_history import PriceHistory


class BasketItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_by_basket(self, basket_id: int) -> int:
        stmt = select(func.count(BasketItem.id)).where(
            BasketItem.basket_id == basket_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(
        self,
        basket_id: int,
        product_url: str,
        product_id: str,
        url_source: str,
        name: str | None,
        quantity: int,
    ) -> BasketItem:
        item = BasketItem(
            basket_id=basket_id,
            product_url=product_url,
            product_id=product_id,
            url_source=url_source,
            name=name,
            quantity=quantity,
        )
        self._session.add(item)
        await self._session.flush()
        return item

    async def get_basket_items_with_latest_price(
        self, basket_id: int
    ) -> list[tuple[BasketItem, Decimal | None, Decimal | None, bool]]:
        """Get all basket items with their latest price record.

        Uses a correlated subquery to fetch the most recent price for each item,
        avoiding N+1 queries.

        Returns list of (BasketItem, price, original_price, is_available) tuples.
        """
        # Subquery: latest price_history row per basket_item
        latest_ph = (
            select(PriceHistory)
            .where(PriceHistory.basket_item_id == BasketItem.id)
            .order_by(PriceHistory.scraped_at.desc())
            .limit(1)
            .correlate(BasketItem)
            .subquery()
            .lateral("latest_price")
        )

        stmt = (
            select(
                BasketItem,
                latest_ph.c.price,
                latest_ph.c.original_price,
                func.coalesce(latest_ph.c.is_available, literal(True)),
            )
            .outerjoin(latest_ph, literal(True))
            .where(BasketItem.basket_id == basket_id)
            .order_by(BasketItem.created_at)
        )
        result = await self._session.execute(stmt)
        return [
            (row[0], row[1], row[2], row[3])
            for row in result.all()
        ]

    async def delete(self, item_id: int) -> None:
        await self._session.execute(
            delete(BasketItem).where(BasketItem.id == item_id)
        )
        await self._session.flush()

    async def get_by_id(self, item_id: int) -> BasketItem | None:
        stmt = select(BasketItem).where(BasketItem.id == item_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_name(self, item_id: int, name: str) -> None:
        item = await self.get_by_id(item_id)
        if item is not None:
            item.name = name
            await self._session.flush()
