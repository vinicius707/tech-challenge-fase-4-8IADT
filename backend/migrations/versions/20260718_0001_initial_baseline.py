"""Cria o baseline inicial do schema.

Revision ID: 20260718_0001
Revises:
Create Date: 2026-07-18 21:19:00
"""

from collections.abc import Sequence

revision: str = "20260718_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Registra o baseline; tabelas de domínio entram nos épicos seguintes."""


def downgrade() -> None:
    """Remove somente o registro desta revisão."""
