"""workspace_config + connector_config + preference tables

Revision ID: 0003_workspace_state
Revises: 0002_event_store
Create Date: 2026-07-02
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_workspace_state"
down_revision = "0002_event_store"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_config",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_table(
        "connector_config",
        sa.Column("connector", sa.String(), primary_key=True),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_table(
        "preference",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("preference")
    op.drop_table("connector_config")
    op.drop_table("workspace_config")
