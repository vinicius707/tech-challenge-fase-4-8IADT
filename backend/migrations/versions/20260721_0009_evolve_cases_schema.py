"""Evolui stub cases e cria modalidades/artefatos.

Revision ID: 20260721_0009
Revises: 20260721_0008
Create Date: 2026-07-21 20:20:00

Épico 3 / T3.6: schema real de Caso + idempotência.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0009"
down_revision: str | Sequence[str] | None = "20260721_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cases",
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
    )
    op.add_column("cases", sa.Column("risk_score", sa.Float(), nullable=True))
    op.add_column("cases", sa.Column("risk_level", sa.String(length=16), nullable=True))
    op.add_column("cases", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.add_column("cases", sa.Column("content_sha256", sa.String(length=64), nullable=True))
    op.add_column(
        "cases",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_unique_constraint("uq_cases_idempotency_key", "cases", ["idempotency_key"])

    op.create_table(
        "artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("modality", sa.String(length=32), nullable=False),
        sa.Column("bucket", sa.String(length=128), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_artifacts_case_id", "artifacts", ["case_id"])

    op.create_table(
        "case_modalities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("modality", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("artifact_id", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(["artifact_id"], ["artifacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_case_modalities_case_id", "case_modalities", ["case_id"])


def downgrade() -> None:
    op.drop_index("ix_case_modalities_case_id", table_name="case_modalities")
    op.drop_table("case_modalities")
    op.drop_index("ix_artifacts_case_id", table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_constraint("uq_cases_idempotency_key", "cases", type_="unique")
    op.drop_column("cases", "updated_at")
    op.drop_column("cases", "content_sha256")
    op.drop_column("cases", "idempotency_key")
    op.drop_column("cases", "risk_level")
    op.drop_column("cases", "risk_score")
    op.drop_column("cases", "status")
