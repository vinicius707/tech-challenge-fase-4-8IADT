"""Adiciona Justificativa JSONB no Caso.

Revision ID: 20260722_0016
Revises: 20260721_0015
Create Date: 2026-07-22 21:05:00

Épico 7 / T7.1: snapshot de Justificativa template após fusão.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260722_0016"
down_revision: str | Sequence[str] | None = "20260721_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cases",
        sa.Column("justification", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cases", "justification")
