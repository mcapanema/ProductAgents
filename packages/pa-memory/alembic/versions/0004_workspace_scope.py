"""workspace scoping: columns, composite keys, registry table

Revision ID: 0004_workspace_scope
Revises: 0003_workspace_state
Create Date: 2026-07-02
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_workspace_scope"
down_revision = "0003_workspace_state"
branch_labels = None
depends_on = None

_ADD_COLUMN = ("memory_decision", "memory_outcome", "runtime_session")


def upgrade() -> None:
    for table in _ADD_COLUMN:
        with op.batch_alter_table(table) as batch:
            batch.add_column(
                sa.Column(
                    "workspace", sa.String(), nullable=False, server_default="default"
                )
            )
        op.create_index(f"ix_{table}_workspace", table, ["workspace"])

    # SQLite can't alter PKs in place; batch mode rebuilds the table.
    with op.batch_alter_table("workspace_config", recreate="always") as batch:
        batch.add_column(
            sa.Column(
                "workspace", sa.String(), nullable=False, server_default="default"
            )
        )
        batch.create_primary_key("pk_workspace_config", ["workspace", "key"])
    with op.batch_alter_table("connector_config", recreate="always") as batch:
        batch.add_column(
            sa.Column(
                "workspace", sa.String(), nullable=False, server_default="default"
            )
        )
        batch.create_primary_key("pk_connector_config", ["workspace", "connector"])

    op.create_table(
        "workspace",
        sa.Column("name", sa.String(), primary_key=True),
        sa.Column("created_at", sa.String(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("workspace")
    with op.batch_alter_table("connector_config", recreate="always") as batch:
        batch.drop_column("workspace")
        batch.create_primary_key("pk_connector_config", ["connector"])
    with op.batch_alter_table("workspace_config", recreate="always") as batch:
        batch.drop_column("workspace")
        batch.create_primary_key("pk_workspace_config", ["key"])
    for table in reversed(_ADD_COLUMN):
        op.drop_index(f"ix_{table}_workspace", table)
        with op.batch_alter_table(table) as batch:
            batch.drop_column("workspace")
