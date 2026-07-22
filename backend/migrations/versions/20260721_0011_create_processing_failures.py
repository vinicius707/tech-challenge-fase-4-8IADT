"""Cria tabela de Falhas de Processamento (DLQ).

Revision ID: 20260721_0011
Revises: 20260721_0010
Create Date: 2026-07-21 22:20:00

Épico 5 / T5.7: painel DLQ admin (ADR 0003).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0011"
down_revision: str | Sequence[str] | None = "20260721_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "processing_failures",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("modality", sa.String(length=32), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
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
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_processing_failures_case_id", "processing_failures", ["case_id"])
    op.create_index(
        "ix_processing_failures_status", "processing_failures", ["status"]
    )


def downgrade() -> None:
    op.drop_index("ix_processing_failures_status", table_name="processing_failures")
    op.drop_index("ix_processing_failures_case_id", table_name="processing_failures")
    op.drop_table("processing_failures")
