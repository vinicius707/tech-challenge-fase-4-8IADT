"""Cria a tabela de Registros de Auditoria.

Revision ID: 20260721_0006
Revises: 20260721_0005
Create Date: 2026-07-21 13:50:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0006"
down_revision: str | Sequence[str] | None = "20260721_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("operator_id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["operator_id"], ["operators.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_records_patient_id", "audit_records", ["patient_id"])
    op.create_index("ix_audit_records_operator_id", "audit_records", ["operator_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_records_operator_id", table_name="audit_records")
    op.drop_index("ix_audit_records_patient_id", table_name="audit_records")
    op.drop_table("audit_records")
