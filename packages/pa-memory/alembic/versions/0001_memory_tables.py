"""memory_decision + memory_outcome tables

Revision ID: 0001_memory_tables
Revises:
Create Date: 2026-06-26
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_memory_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memory_decision",
        sa.Column("decision_id", sa.String(), primary_key=True),
        sa.Column("initiative_title", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_table(
        "memory_outcome",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("decision_id", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("reflected_at", sa.String(), nullable=False),
    )
    op.create_index("ix_memory_outcome_decision_id", "memory_outcome", ["decision_id"])


def downgrade() -> None:
    op.drop_index("ix_memory_outcome_decision_id", table_name="memory_outcome")
    op.drop_table("memory_outcome")
    op.drop_table("memory_decision")
