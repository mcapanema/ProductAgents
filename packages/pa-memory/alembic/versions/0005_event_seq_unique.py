"""unique (session_id, seq) on runtime_event

Revision ID: 0005_event_seq_unique
Revises: 0004_workspace_scope
Create Date: 2026-07-07

ponytail: batch_alter_table recreates the table on SQLite to add the constraint;
it fails if a legacy DB already holds duplicate (session_id, seq) rows. That's an
acceptable ceiling for a local single-user DB — the runtime IntegrityError
tolerance in EventStore.append is the primary guard; dedup here only if a real
migration ever trips on duplicates.
"""

from alembic import op

revision = "0005_event_seq_unique"
down_revision = "0004_workspace_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("runtime_event") as batch:
        batch.create_unique_constraint(
            "uq_runtime_event_session_seq", ["session_id", "seq"]
        )


def downgrade() -> None:
    with op.batch_alter_table("runtime_event") as batch:
        batch.drop_constraint("uq_runtime_event_session_seq", type_="unique")
