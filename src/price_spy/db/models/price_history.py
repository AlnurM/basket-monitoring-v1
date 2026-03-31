from __future__ import annotations

import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .basket_item import BasketItem


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (
        Index("idx_price_history_item_date", "basket_item_id", "scraped_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    basket_item_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("basket_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    original_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    scraped_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    basket_item: Mapped["BasketItem"] = relationship(back_populates="price_records")
