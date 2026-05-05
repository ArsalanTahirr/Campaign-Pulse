"""Add pipeline_status column to lead table

Revision ID: a9b0c1d2e3f4
Revises: f7a8b9c0d1e2
Create Date: 2026-05-01 19:10:00.000000

Adds pipeline_status (VARCHAR 30) to the lead table to track where a lead
is in the sales funnel for the Unibox Status sidebar view. This is
semantically distinct from lead_status (deliverability state) and the two
columns coexist independently.

All existing leads receive the default value 'lead'. PostgreSQL adds a
NOT NULL column with a constant DEFAULT in a metadata-only operation
(no table rewrite) since PG 11+, making this zero-downtime.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a9b0c1d2e3f4"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_VALID_VALUES = "('lead','interested','meeting-booked','meeting-completed','won')"


def upgrade() -> None:
    """Add pipeline_status column to lead with default, constraint, and index."""
    op.add_column(
        "lead",
        sa.Column(
            "pipeline_status",
            sa.String(30),
            nullable=False,
            server_default=sa.text("'lead'"),
            comment=(
                "Sales pipeline stage for the Unibox Status view. "
                "Values: lead | interested | meeting-booked | meeting-completed | won. "
                "Independent of lead_status (deliverability)."
            ),
        ),
    )

    op.create_check_constraint(
        "ck_lead_pipeline_status",
        "lead",
        f"pipeline_status IN {_VALID_VALUES}",
    )

    op.create_index(
        "idx_lead_pipeline_status",
        "lead",
        ["pipeline_status"],
    )


def downgrade() -> None:
    """Remove pipeline_status column and its constraint/index from lead."""
    op.drop_index("idx_lead_pipeline_status", table_name="lead")
    op.drop_constraint("ck_lead_pipeline_status", "lead", type_="check")
    op.drop_column("lead", "pipeline_status")
