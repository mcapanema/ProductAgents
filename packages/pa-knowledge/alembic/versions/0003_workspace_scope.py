"""workspace scoping for canonical_record + sync_state

Revision ID: 0003_workspace_scope
Revises: 0002_sync_state
Create Date: 2026-07-02
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_workspace_scope"
down_revision = "0002_sync_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("canonical_record", recreate="always") as batch:
        batch.add_column(
            sa.Column(
                "workspace", sa.String(), nullable=False, server_default="default"
            )
        )
        batch.drop_constraint("uq_canonical_source", type_="unique")
        batch.create_unique_constraint(
            "uq_canonical_source",
            ["workspace", "connector", "vendor_type", "vendor_id"],
        )
    op.create_index("ix_canonical_record_workspace", "canonical_record", ["workspace"])

    with op.batch_alter_table("sync_state", recreate="always") as batch:
        batch.add_column(
            sa.Column(
                "workspace", sa.String(), nullable=False, server_default="default"
            )
        )
        batch.create_primary_key("pk_sync_state", ["workspace", "connector_key"])


def downgrade() -> None:
    with op.batch_alter_table("sync_state", recreate="always") as batch:
        batch.drop_column("workspace")
        batch.create_primary_key("pk_sync_state", ["connector_key"])
    op.drop_index("ix_canonical_record_workspace", "canonical_record")
    with op.batch_alter_table("canonical_record", recreate="always") as batch:
        batch.drop_constraint("uq_canonical_source", type_="unique")
        batch.create_unique_constraint(
            "uq_canonical_source", ["connector", "vendor_type", "vendor_id"]
        )
        batch.drop_column("workspace")
