from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from price_spy.db.models.basket import Basket
from price_spy.db.models.basket_item import BasketItem


class BasketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_baskets(self, user_id: int) -> list[Basket]:
        stmt = (
            select(Basket)
            .where(Basket.user_id == user_id)
            .order_by(Basket.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_baskets_with_item_counts(
        self, user_id: int
    ) -> list[tuple[Basket, int]]:
        item_count = (
            select(func.count(BasketItem.id))
            .where(BasketItem.basket_id == Basket.id)
            .correlate(Basket)
            .scalar_subquery()
        )
        stmt = (
            select(Basket, item_count)
            .where(Basket.user_id == user_id)
            .order_by(Basket.created_at)
        )
        result = await self._session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def count_by_user(self, user_id: int) -> int:
        stmt = select(func.count(Basket.id)).where(Basket.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, user_id: int, name: str, source: str) -> Basket:
        basket = Basket(user_id=user_id, name=name, source=source)
        self._session.add(basket)
        await self._session.flush()
        return basket

    async def get_by_id(self, basket_id: int) -> Basket | None:
        stmt = select(Basket).where(Basket.id == basket_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_basket(self, user_id: int) -> Basket | None:
        stmt = (
            select(Basket)
            .where(Basket.user_id == user_id, Basket.is_active.is_(True))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_active(self, user_id: int, basket_id: int) -> None:
        # Deactivate all user baskets
        await self._session.execute(
            update(Basket)
            .where(Basket.user_id == user_id)
            .values(is_active=False)
        )
        # Activate target basket
        await self._session.execute(
            update(Basket)
            .where(Basket.id == basket_id)
            .values(is_active=True)
        )
        await self._session.flush()

    async def delete(self, basket_id: int) -> None:
        await self._session.execute(
            delete(Basket).where(Basket.id == basket_id)
        )
        await self._session.flush()
