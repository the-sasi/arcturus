"""Create instruments table

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "instruments",
        sa.Column("symbol", sa.String(length=40), nullable=False),
        sa.Column("exchange", sa.String(length=16), nullable=False),
        sa.Column("ticker", sa.String(length=24), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("asset_class", sa.String(length=16), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("symbol", name=op.f("pk_instruments")),
    )
    op.create_index(op.f("ix_instruments_exchange"), "instruments", ["exchange"])
    op.create_index(op.f("ix_instruments_name"), "instruments", ["name"])


def downgrade() -> None:
    op.drop_index(op.f("ix_instruments_name"), table_name="instruments")
    op.drop_index(op.f("ix_instruments_exchange"), table_name="instruments")
    op.drop_table("instruments")
