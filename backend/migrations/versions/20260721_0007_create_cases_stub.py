"""Cria stub da tabela cases com FK CASCADE para patients.

Revision ID: 20260721_0007
Revises: 20260721_0006
Create Date: 2026-07-21 13:55:00

Preparação do Épico 2 (cenário 10 da spec de Paciente): materializa
`cases.patient_id → patients.id ON DELETE CASCADE`. A API de Caso permanece
fora do escopo até o Épico 3.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0007"
down_revision: str | Sequence[str] | None = "20260721_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cases_patient_id", "cases", ["patient_id"])


def downgrade() -> None:
    op.drop_index("ix_cases_patient_id", table_name="cases")
    op.drop_table("cases")
