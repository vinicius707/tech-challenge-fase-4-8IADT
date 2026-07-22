"""Adiciona idempotência de upload de vídeo no Caso.

Revision ID: 20260721_0012
Revises: 20260721_0011
Create Date: 2026-07-21 22:40:00

Épico 6 / T6.2: POST /cases/{id}/modalities/video.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0012"
down_revision: str | Sequence[str] | None = "20260721_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cases",
        sa.Column("video_idempotency_key", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "cases",
        sa.Column("video_content_sha256", sa.String(length=64), nullable=True),
    )
    op.create_unique_constraint(
        "uq_cases_video_idempotency_key", "cases", ["video_idempotency_key"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_cases_video_idempotency_key", "cases", type_="unique")
    op.drop_column("cases", "video_content_sha256")
    op.drop_column("cases", "video_idempotency_key")
