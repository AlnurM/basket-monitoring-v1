"""add product_name_cache table (SCRP-05)

Revision ID: 002
Revises: 001
Create Date: 2026-03-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_name_cache",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("product_url", sa.Text(), nullable=False, unique=True),
        sa.Column("url_source", sa.String(10), nullable=False),
        sa.Column("product_id", sa.String(50), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("product_name_cache")
