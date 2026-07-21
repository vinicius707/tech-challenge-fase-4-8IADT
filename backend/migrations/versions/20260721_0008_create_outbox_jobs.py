"""Cria tabela outbox_jobs para despacho assíncrono via RQ.

Revision ID: 20260721_0008
Revises: 20260721_0007
Create Date: 2026-07-21 20:00:00

Épico 3 / T3.3: Postgres é a fonte da verdade; Redis/RQ apenas despacha.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260721_0008"
down_revision: str | Sequence[str] | None = "20260721_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outbox_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("rq_job_id", sa.String(length=128), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outbox_jobs_status", "outbox_jobs", ["status"])
    op.create_index(
        "ix_outbox_jobs_aggregate",
        "outbox_jobs",
        ["aggregate_type", "aggregate_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_jobs_aggregate", table_name="outbox_jobs")
    op.drop_index("ix_outbox_jobs_status", table_name="outbox_jobs")
    op.drop_table("outbox_jobs")
