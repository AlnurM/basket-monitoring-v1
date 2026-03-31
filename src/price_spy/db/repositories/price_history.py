import datetime
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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

    async def get_price_range(
        self,
        basket_item_ids: list[int],
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[PriceHistory]:
        """Get all price history records in a date range for given items.

        Returns records ordered by scraped_at ASC.
        Used by charts and export features.
        """
        if not basket_item_ids:
            return []

        stmt = (
            select(PriceHistory)
            .where(
                PriceHistory.basket_item_id.in_(basket_item_ids),
                PriceHistory.scraped_at >= start_date,
                PriceHistory.scraped_at <= end_date,
            )
            .order_by(PriceHistory.scraped_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_first_prices_in_range(
        self,
        basket_item_ids: list[int],
        start_date: datetime.datetime,
    ) -> dict[int, tuple[Decimal | None, bool]]:
        """Get the earliest price record for each item after start_date.

        Returns dict mapping basket_item_id to (price, is_available).
        Uses DISTINCT ON with ASC order (opposite of get_previous_prices).
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
                PriceHistory.scraped_at >= start_date,
            )
            .distinct(PriceHistory.basket_item_id)
            .order_by(
                PriceHistory.basket_item_id,
                PriceHistory.scraped_at.asc(),
            )
        )
        result = await self._session.execute(stmt)
        return {
            row[0]: (row[1], row[2])
            for row in result.all()
        }

    async def get_daily_basket_totals(
        self,
        basket_item_ids: list[int],
        quantities: dict[int, int],
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[tuple[datetime.date, Decimal]]:
        """Get daily basket totals for charting.

        For each day in range, computes sum(last_price_per_item * quantity).
        Uses Python-side aggregation for clarity (max ~4500 records for 90 days * 50 items).

        Returns list of (date, total) sorted by date.
        """
        records = await self.get_price_range(basket_item_ids, start_date, end_date)
        if not records:
            return []

        # Group by date, then by item — keep last price per item per day
        # dict[date, dict[item_id, price]]
        daily_prices: dict[datetime.date, dict[int, Decimal]] = defaultdict(dict)

        for rec in records:
            day = rec.scraped_at.date()
            if rec.price is not None:
                daily_prices[day][rec.basket_item_id] = rec.price

        # Compute daily totals
        result: list[tuple[datetime.date, Decimal]] = []
        for day in sorted(daily_prices.keys()):
            item_prices = daily_prices[day]
            total = sum(
                price * quantities.get(item_id, 1)
                for item_id, price in item_prices.items()
            )
            result.append((day, Decimal(total)))

        return result

    async def get_export_data(
        self,
        basket_item_ids: list[int],
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[PriceHistory]:
        """Get price history with eagerly loaded basket_item for export.

        Same as get_price_range but includes basket_item relationship
        (for product name and quantity) to avoid N+1 queries.
        """
        if not basket_item_ids:
            return []

        stmt = (
            select(PriceHistory)
            .options(selectinload(PriceHistory.basket_item))
            .where(
                PriceHistory.basket_item_id.in_(basket_item_ids),
                PriceHistory.scraped_at >= start_date,
                PriceHistory.scraped_at <= end_date,
            )
            .order_by(PriceHistory.scraped_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
