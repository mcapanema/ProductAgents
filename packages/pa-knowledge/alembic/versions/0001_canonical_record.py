"""create canonical_record

Revision ID: 0001_canonical_record
Revises:
Create Date: 2026-06-23 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_canonical_record"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "canonical_record",
        sa.Column("pk", sa.String(), nullable=False),
        sa.Column("model_type", sa.String(), nullable=False),
        sa.Column("connector", sa.String(), nullable=False),
        sa.Column("vendor_type", sa.String(), nullable=False),
        sa.Column("vendor_id", sa.String(), nullable=True),
        sa.Column("raw_fingerprint", sa.String(), nullable=True),
        sa.Column("ingested_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("pk"),
        sa.UniqueConstraint(
            "connector", "vendor_type", "vendor_id", name="uq_canonical_source"
        ),
    )
    op.create_index(
        "ix_canonical_record_model_type", "canonical_record", ["model_type"]
    )
    op.create_index("ix_canonical_record_vendor_id", "canonical_record", ["vendor_id"])


def downgrade() -> None:
    op.drop_index("ix_canonical_record_vendor_id", table_name="canonical_record")
    op.drop_index("ix_canonical_record_model_type", table_name="canonical_record")
    op.drop_table("canonical_record")
