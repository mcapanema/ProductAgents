"""runtime_session + runtime_event tables

Revision ID: 0002_event_store
Revises: 0001_memory_tables
Create Date: 2026-06-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_event_store"
down_revision = "0001_memory_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runtime_session",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workflow", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_table(
        "runtime_event",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("ts", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_index("ix_runtime_event_session_id", "runtime_event", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_runtime_event_session_id", table_name="runtime_event")
    op.drop_table("runtime_event")
    op.drop_table("runtime_session")
