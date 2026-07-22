"""Adiciona provider na modalidade do Caso (áudio Azure/local/cache).

Revision ID: 20260721_0014
Revises: 20260721_0013
Create Date: 2026-07-21 23:15:00

Épico 6 / T6.10: Provedor de Áudio persistido na modalidade.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0014"
down_revision: str | Sequence[str] | None = "20260721_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "case_modalities",
        sa.Column("provider", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("case_modalities", "provider")
