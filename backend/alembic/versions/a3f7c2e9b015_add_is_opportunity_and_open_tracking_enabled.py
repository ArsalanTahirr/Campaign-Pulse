"""Add is_opportunity to lead and open_tracking_enabled to campaign

Revision ID: a3f7c2e9b015
Revises: c3f2e8a7b901
Create Date: 2026-05-01 11:50:00.000000

SC-REQUEST #1: is_opportunity (Boolean) on lead table.
  Flags a lead's reply as a high-quality opportunity (e.g. interested lead,
  demo request).  Default False — all existing leads are not opportunities
  until a user or automation explicitly marks them.

SC-REQUEST #2: open_tracking_enabled (Boolean) on campaign table.
  Controls whether open-tracking pixels are injected into outbound emails.
  Default True — all existing campaigns retain their current behaviour.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a3f7c2e9b015'
down_revision: Union[str, None] = 'c3f2e8a7b901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_opportunity to lead and open_tracking_enabled to campaign."""
    op.add_column(
        'lead',
        sa.Column(
            'is_opportunity',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
            comment='True when this lead\'s reply is flagged as a high-quality opportunity.',
        ),
    )

    op.add_column(
        'campaign',
        sa.Column(
            'open_tracking_enabled',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('true'),
            comment='When False, open-tracking pixels are not injected and opens are not recorded.',
        ),
    )


def downgrade() -> None:
    """Remove is_opportunity from lead and open_tracking_enabled from campaign."""
    op.drop_column('campaign', 'open_tracking_enabled')
    op.drop_column('lead', 'is_opportunity')
