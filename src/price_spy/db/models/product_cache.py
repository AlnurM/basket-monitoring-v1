"""Cached product names — SCRP-05: no re-extraction needed after first scrape."""

from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ProductNameCache(Base):
    """Stores product names by URL so subsequent scrapes skip name extraction."""

    __tablename__ = "product_name_cache"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    url_source: Mapped[str] = mapped_column(String(10), nullable=False)
    product_id: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
