from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .basket import Basket
    from .price_history import PriceHistory


class BasketItem(Base):
    __tablename__ = "basket_items"
    __table_args__ = (
        UniqueConstraint("basket_id", "product_url", name="uq_basket_item_url"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    basket_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("baskets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_url: Mapped[str] = mapped_column(Text, nullable=False)
    product_id: Mapped[str] = mapped_column(Text, nullable=False)
    url_source: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    basket: Mapped["Basket"] = relationship(back_populates="items")
    price_records: Mapped[list["PriceHistory"]] = relationship(
        back_populates="basket_item", cascade="all, delete-orphan"
    )
