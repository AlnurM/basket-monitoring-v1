from __future__ import annotations

import datetime

from sqlalchemy import BigInteger, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    username: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(Text, nullable=False, default="en")
    notify_time: Mapped[datetime.time] = mapped_column(
        Time, default=datetime.time(9, 0)
    )
    timezone: Mapped[str] = mapped_column(Text, default="Asia/Almaty")
    created_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
