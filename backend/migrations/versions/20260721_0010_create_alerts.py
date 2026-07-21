"""Cria tabela de Alertas versionados (v1).

Revision ID: 20260721_0010
Revises: 20260721_0009
Create Date: 2026-07-21 23:40:00

Épico 3 / T3.9: Alerta v1 se Risco ≥ MEDIO.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0010"
down_revision: str | Sequence[str] | None = "20260721_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "case_id", "level", "version", name="uq_alerts_case_level_version"
        ),
    )
    op.create_index("ix_alerts_case_id", "alerts", ["case_id"])


def downgrade() -> None:
    op.drop_index("ix_alerts_case_id", table_name="alerts")
    op.drop_table("alerts")
