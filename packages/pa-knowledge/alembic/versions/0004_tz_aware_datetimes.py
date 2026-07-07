"""Timezone-aware datetime columns.

canonical_record.ingested_at/updated_at and sync_state.updated_at were naive
DateTime columns even though every value written into them is tz-aware
(datetime.now(UTC)) — SQLite silently truncated the offset, so a read-back
.isoformat() looked indistinguishable from local time. Existing values are
UTC already; SQLite has no real column-type migration, so this is a
schema-only change (batch recreate), not a data rewrite.

Revision ID: 0004_tz_aware_datetimes
Revises: 0003_workspace_scope
Create Date: 2026-07-07
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_tz_aware_datetimes"
down_revision = "0003_workspace_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("canonical_record", recreate="always") as batch_op:
        batch_op.alter_column(
            "ingested_at", type_=sa.DateTime(timezone=True), existing_nullable=False
        )
        batch_op.alter_column(
            "updated_at", type_=sa.DateTime(timezone=True), existing_nullable=False
        )
    with op.batch_alter_table("sync_state", recreate="always") as batch_op:
        batch_op.alter_column(
            "updated_at", type_=sa.DateTime(timezone=True), existing_nullable=False
        )


def downgrade() -> None:
    with op.batch_alter_table("canonical_record", recreate="always") as batch_op:
        batch_op.alter_column(
            "ingested_at", type_=sa.DateTime(timezone=False), existing_nullable=False
        )
        batch_op.alter_column(
            "updated_at", type_=sa.DateTime(timezone=False), existing_nullable=False
        )
    with op.batch_alter_table("sync_state", recreate="always") as batch_op:
        batch_op.alter_column(
            "updated_at", type_=sa.DateTime(timezone=False), existing_nullable=False
        )
