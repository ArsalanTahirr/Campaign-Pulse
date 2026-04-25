"""s5_backfill_and_drop_sequence_step_content

Revision ID: c2e7f9a1b4d3
Revises: 764aa51766e6
Create Date: 2026-04-25 20:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2e7f9a1b4d3"
down_revision: Union[str, None] = "764aa51766e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Finalize S5 migration:
    1) backfill old sequence_step content into step_email (if variants missing),
    2) drop deprecated sequence_step.subject_line/email_body columns.
    """
    op.execute(
        """
        INSERT INTO step_email (
            email_id,
            step_id,
            subject_line,
            email_body,
            from_name,
            sender_account_id,
            created_at
        )
        SELECT
            gen_random_uuid(),
            ss.step_id,
            ss.subject_line,
            ss.email_body,
            NULL,
            NULL,
            now()
        FROM sequence_step ss
        WHERE ss.subject_line IS NOT NULL
          AND ss.email_body IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM step_email se
              WHERE se.step_id = ss.step_id
          );
        """
    )

    op.drop_column("sequence_step", "email_body")
    op.drop_column("sequence_step", "subject_line")


def downgrade() -> None:
    """
    Restore deprecated columns for rollback compatibility and repopulate them
    from the earliest variant per step when available.
    """
    op.add_column(
        "sequence_step",
        sa.Column(
            "subject_line",
            sa.String(length=998),
            nullable=True,
            comment="DEPRECATED — use step_email.subject_line. Kept nullable during migration.",
        ),
    )
    op.add_column(
        "sequence_step",
        sa.Column(
            "email_body",
            sa.Text(),
            nullable=True,
            comment="DEPRECATED — use step_email.email_body. Kept nullable during migration.",
        ),
    )

    op.execute(
        """
        WITH first_variant AS (
            SELECT DISTINCT ON (se.step_id)
                se.step_id,
                se.subject_line,
                se.email_body
            FROM step_email se
            ORDER BY se.step_id, se.created_at ASC
        )
        UPDATE sequence_step ss
        SET
            subject_line = fv.subject_line,
            email_body = fv.email_body
        FROM first_variant fv
        WHERE fv.step_id = ss.step_id;
        """
    )
