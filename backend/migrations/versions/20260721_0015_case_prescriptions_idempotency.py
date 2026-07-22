"""Adiciona idempotência de upload de prescrições no Caso.

Revision ID: 20260721_0015
Revises: 20260721_0014
Create Date: 2026-07-21 23:40:00

Épico 6 / T6.15: POST /cases/{id}/modalities/prescriptions.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0015"
down_revision: str | Sequence[str] | None = "20260721_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cases",
        sa.Column(
            "prescriptions_idempotency_key", sa.String(length=128), nullable=True
        ),
    )
    op.add_column(
        "cases",
        sa.Column("prescriptions_content_sha256", sa.String(length=64), nullable=True),
    )
    op.create_unique_constraint(
        "uq_cases_prescriptions_idempotency_key",
        "cases",
        ["prescriptions_idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_cases_prescriptions_idempotency_key", "cases", type_="unique"
    )
    op.drop_column("cases", "prescriptions_content_sha256")
    op.drop_column("cases", "prescriptions_idempotency_key")
