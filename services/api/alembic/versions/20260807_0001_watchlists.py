"""Create watchlists and watchlist_items tables

Revision ID: 0001
Revises:
Create Date: 2026-08-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "watchlists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_watchlists")),
        sa.UniqueConstraint("name", name=op.f("uq_watchlists_name")),
    )
    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("watchlist_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(length=40), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["watchlist_id"],
            ["watchlists.id"],
            name=op.f("fk_watchlist_items_watchlist_id_watchlists"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_watchlist_items")),
        sa.UniqueConstraint("watchlist_id", "symbol", name=op.f("uq_watchlist_items_watchlist_id")),
    )


def downgrade() -> None:
    op.drop_table("watchlist_items")
    op.drop_table("watchlists")
