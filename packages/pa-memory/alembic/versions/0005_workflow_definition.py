"""workflow_definition table

Revision ID: 0005_workflow_definition
Revises: 0004_workspace_scope
Create Date: 2026-07-04
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_workflow_definition"
down_revision = "0004_workspace_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_definition",
        sa.Column("workspace", sa.String(), server_default="default", nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("builtin", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("workspace", "name"),
    )


def downgrade() -> None:
    op.drop_table("workflow_definition")
