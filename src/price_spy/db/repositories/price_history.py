import datetime
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from price_spy.db.models.price_history import PriceHistory


class PriceHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        basket_item_id: int,
        price: Decimal | None,
        original_price: Decimal | None,
        is_available: bool,
    ) -> PriceHistory:
        record = PriceHistory(
            basket_item_id=basket_item_id,
            price=price,
            original_price=original_price,
            is_available=is_available,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def cleanup_old_records(self, retention_days: int) -> int:
        """Delete price history records older than retention_days.

        Returns the count of deleted records.
        """
        cutoff = func.now() - datetime.timedelta(days=retention_days)
        stmt = delete(PriceHistory).where(PriceHistory.scraped_at < cutoff)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    async def get_previous_prices(
        self,
        basket_item_ids: list[int],
        before: datetime.datetime,
    ) -> dict[int, tuple[Decimal | None, bool]]:
        """Get the most recent price for each basket_item before a cutoff time.

        Returns dict mapping basket_item_id to (price, is_available).
        Uses DISTINCT ON for PostgreSQL efficiency.
        """
        if not basket_item_ids:
            return {}

        stmt = (
            select(
                PriceHistory.basket_item_id,
                PriceHistory.price,
                PriceHistory.is_available,
            )
            .where(
                PriceHistory.basket_item_id.in_(basket_item_ids),
                PriceHistory.scraped_at < before,
            )
            .distinct(PriceHistory.basket_item_id)
            .order_by(
                PriceHistory.basket_item_id,
                PriceHistory.scraped_at.desc(),
            )
        )
        result = await self._session.execute(stmt)
        return {
            row[0]: (row[1], row[2])
            for row in result.all()
        }
