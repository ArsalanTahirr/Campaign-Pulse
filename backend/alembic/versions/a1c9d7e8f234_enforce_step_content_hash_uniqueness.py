"""enforce step content hash uniqueness

Revision ID: a1c9d7e8f234
Revises: 0ff55274753b
Create Date: 2026-04-27 01:12:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1c9d7e8f234"
down_revision: Union[str, None] = "0ff55274753b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_step_email_step_content_hash",
        "step_email",
        ["step_id", "content_hash"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_step_email_step_content_hash", "step_email", type_="unique")

