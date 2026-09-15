"""Shared data platform foundation: companies, identifiers, conflicts, experiment quality

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("country", sa.String(length=8), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_companies")),
    )
    op.create_table(
        "company_identifiers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("scheme", sa.String(length=16), nullable=False),
        sa.Column("value", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_company_identifiers_company_id_companies"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_company_identifiers")),
        sa.UniqueConstraint(
            "company_id", "scheme", "value", name=op.f("uq_company_identifiers_company_id")
        ),
    )
    op.create_index(
        op.f("ix_company_identifiers_company_id"), "company_identifiers", ["company_id"]
    )
    op.create_index(
        "ix_company_identifiers_scheme_value", "company_identifiers", ["scheme", "value"]
    )
    op.create_table(
        "data_conflicts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conflict_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("subject", sa.String(length=128), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("source_a_id", sa.String(length=64), nullable=False),
        sa.Column("value_a", sa.String(length=255), nullable=True),
        sa.Column("source_b_id", sa.String(length=64), nullable=False),
        sa.Column("value_b", sa.String(length=255), nullable=True),
        sa.Column("classification", sa.String(length=32), nullable=False),
        sa.Column("resolution_status", sa.String(length=16), nullable=False),
        sa.Column("preferred_source_id", sa.String(length=64), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["companies.id"],
            name=op.f("fk_data_conflicts_entity_id_companies"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_conflicts")),
    )
    op.create_index(op.f("ix_data_conflicts_entity_id"), "data_conflicts", ["entity_id"])
    op.create_index(op.f("ix_data_conflicts_subject"), "data_conflicts", ["subject"])
    op.create_index(
        op.f("ix_data_conflicts_resolution_status"), "data_conflicts", ["resolution_status"]
    )
    op.add_column("experiments", sa.Column("data_quality", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("experiments", "data_quality")
    op.drop_index(op.f("ix_data_conflicts_resolution_status"), table_name="data_conflicts")
    op.drop_index(op.f("ix_data_conflicts_subject"), table_name="data_conflicts")
    op.drop_index(op.f("ix_data_conflicts_entity_id"), table_name="data_conflicts")
    op.drop_table("data_conflicts")
    op.drop_index("ix_company_identifiers_scheme_value", table_name="company_identifiers")
    op.drop_index(op.f("ix_company_identifiers_company_id"), table_name="company_identifiers")
    op.drop_table("company_identifiers")
    op.drop_table("companies")
