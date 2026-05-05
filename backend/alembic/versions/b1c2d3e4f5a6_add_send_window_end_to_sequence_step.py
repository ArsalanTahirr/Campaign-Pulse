"""Add send_window_end to sequence_step for daily send windows

Revision ID: b1c2d3e4f5a6
Revises: a9b0c1d2e3f4
Create Date: 2026-05-03 12:00:00.000000

Local send window end (HH:MM) in campaign timezone. send_time is window start.
NULL means end equals start (legacy single-instant behavior).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "a9b0c1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sequence_step",
        sa.Column(
            "send_window_end",
            sa.String(length=5),
            nullable=True,
            comment="End of daily send window (HH:MM, 24-hour) in campaign timezone; null = same as send_time.",
        ),
    )


def downgrade() -> None:
    op.drop_column("sequence_step", "send_window_end")
