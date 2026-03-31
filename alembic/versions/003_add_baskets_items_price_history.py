"""add baskets, basket_items, price_history tables

Revision ID: 003
Revises: 002
Create Date: 2026-03-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "baskets",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source IN ('arbuz', 'magnum')", name="ck_baskets_source"
        ),
    )

    op.create_table(
        "basket_items",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "basket_id",
            sa.BigInteger,
            sa.ForeignKey("baskets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("product_url", sa.Text, nullable=False),
        sa.Column("product_id", sa.Text, nullable=False),
        sa.Column("url_source", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=True),
        sa.Column("quantity", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column(
            "created_at",
            sa.DateTime,
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("basket_id", "product_url", name="uq_basket_item_url"),
        sa.CheckConstraint(
            "url_source IN ('arbuz', 'magnum', 'kaspi')",
            name="ck_items_url_source",
        ),
    )

    op.create_table(
        "price_history",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "basket_item_id",
            sa.BigInteger,
            sa.ForeignKey("basket_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("original_price", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "is_available",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "scraped_at",
            sa.DateTime,
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "idx_price_history_item_date",
        "price_history",
        ["basket_item_id", sa.text("scraped_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_price_history_item_date", table_name="price_history")
    op.drop_table("price_history")
    op.drop_table("basket_items")
    op.drop_table("baskets")
