"""create sync_state

Revision ID: 0002_sync_state
Revises: 0001_canonical_record
Create Date: 2026-06-26 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_sync_state"
down_revision = "0001_canonical_record"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sync_state",
        sa.Column("connector_key", sa.String(), nullable=False),
        sa.Column("cursor_value", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("connector_key"),
    )


def downgrade() -> None:
    op.drop_table("sync_state")
