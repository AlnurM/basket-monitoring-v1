"""Repository for product name cache — SCRP-05."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from price_spy.db.models.product_cache import ProductNameCache


class ProductCacheRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_name(self, product_url: str) -> str | None:
        """Return cached name for URL, or None if not cached."""
        stmt = select(ProductNameCache.name).where(
            ProductNameCache.product_url == product_url
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_name(
        self, product_url: str, url_source: str, product_id: str, name: str
    ) -> None:
        """Cache a product name. Upsert — overwrites if URL already exists."""
        existing = await self._session.execute(
            select(ProductNameCache).where(
                ProductNameCache.product_url == product_url
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            row.name = name
        else:
            self._session.add(
                ProductNameCache(
                    product_url=product_url,
                    url_source=url_source,
                    product_id=product_id,
                    name=name,
                )
            )
        await self._session.flush()
