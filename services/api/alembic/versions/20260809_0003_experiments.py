"""Create experiments table (research registry, ADR-008)

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "experiments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("strategy_key", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=16), nullable=False),
        sa.Column("symbol", sa.String(length=40), nullable=False),
        sa.Column("interval", sa.String(length=8), nullable=False),
        sa.Column("start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bars", sa.Integer(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("engine_version", sa.String(length=16), nullable=False),
        sa.Column("validation", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_experiments")),
    )
    op.create_index(op.f("ix_experiments_strategy_key"), "experiments", ["strategy_key"])
    op.create_index(op.f("ix_experiments_symbol"), "experiments", ["symbol"])


def downgrade() -> None:
    op.drop_index(op.f("ix_experiments_symbol"), table_name="experiments")
    op.drop_index(op.f("ix_experiments_strategy_key"), table_name="experiments")
    op.drop_table("experiments")
