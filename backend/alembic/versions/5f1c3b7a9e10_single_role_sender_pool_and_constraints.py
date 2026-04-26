"""single role sender pool and additional constraints

Revision ID: 5f1c3b7a9e10
Revises: b43dc71647d6
Create Date: 2026-04-26 23:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "5f1c3b7a9e10"
down_revision: Union[str, None] = "b43dc71647d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Campaign sender pool (M:N between campaign and sender_account)
    op.create_table(
        "campaign_sender_pool",
        sa.Column("campaign_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("sender_account_id", sa.UUID(as_uuid=False), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaign.campaign_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sender_account_id"],
            ["sender_account.account_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("campaign_id", "sender_account_id"),
    )

    # 2) Single-role collaborator model (drop collaborator_role)
    op.add_column("collaborator", sa.Column("role_id", sa.UUID(as_uuid=False), nullable=True))
    op.create_foreign_key(
        "fk_collaborator_role_id_role",
        "collaborator",
        "role",
        ["role_id"],
        ["role_id"],
        ondelete="RESTRICT",
    )

    # Best-effort backfill from collaborator_role where present.
    op.execute(
        """
        UPDATE collaborator c
        SET role_id = cr.role_id
        FROM collaborator_role cr
        WHERE cr.member_id = c.member_id
          AND c.role_id IS NULL;
        """
    )
    # Fill any remaining NULL role_id with Owner role if present.
    op.execute(
        """
        UPDATE collaborator c
        SET role_id = r.role_id
        FROM role r
        WHERE c.role_id IS NULL
          AND r.role_name = 'Owner';
        """
    )
    op.alter_column("collaborator", "role_id", nullable=False)

    # 3) Remove fixed sender binding from step_email
    op.execute("ALTER TABLE step_email DROP CONSTRAINT IF EXISTS step_email_sender_account_id_fkey")
    op.execute("ALTER TABLE step_email DROP CONSTRAINT IF EXISTS fk_step_email_sender_account_id_sender_account")
    op.drop_column("step_email", "sender_account_id")

    # 4) Drop old multi-role assignment table
    op.drop_table("collaborator_role")

    # 5) Additional DB-level constraints
    op.create_check_constraint(
        "ck_collaborator_invite_status",
        "collaborator",
        "invite_status IN ('pending','accepted','declined')",
    )
    op.create_check_constraint(
        "ck_invitation_status",
        "invitation",
        "status IN ('pending','accepted','declined','cancelled','expired')",
    )
    op.create_check_constraint(
        "ck_campaign_run_action",
        "campaign_run",
        "action IN ('started','paused','resumed','stopped','completed')",
    )
    op.create_check_constraint(
        "ck_campaign_run_status",
        "campaign_run",
        "run_status IN ('running','paused','stopped','completed','error')",
    )

    # One pending invitation per workspace/email.
    op.create_index(
        "uq_invitation_pending_workspace_email",
        "invitation",
        ["workspace_id", "invitee_email"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    # Case-insensitive unique user email.
    op.create_index(
        "uq_users_email_lower",
        "users",
        [sa.text("lower(email)")],
        unique=True,
    )


def downgrade() -> None:
    # Drop added indexes/constraints first
    op.drop_index("uq_users_email_lower", table_name="users")
    op.drop_index("uq_invitation_pending_workspace_email", table_name="invitation")
    op.drop_constraint("ck_campaign_run_status", "campaign_run", type_="check")
    op.drop_constraint("ck_campaign_run_action", "campaign_run", type_="check")
    op.drop_constraint("ck_invitation_status", "invitation", type_="check")
    op.drop_constraint("ck_collaborator_invite_status", "collaborator", type_="check")

    # Recreate collaborator_role table
    op.create_table(
        "collaborator_role",
        sa.Column("member_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("role_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "assigned_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("assigned_by", sa.UUID(as_uuid=False), nullable=True),
        sa.ForeignKeyConstraint(["member_id"], ["collaborator.member_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["role.role_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("member_id", "role_id"),
    )

    # Backfill collaborator_role from collaborator.role_id
    op.execute(
        """
        INSERT INTO collaborator_role (member_id, role_id, assigned_at)
        SELECT member_id, role_id, now()
        FROM collaborator
        WHERE role_id IS NOT NULL
        ON CONFLICT (member_id, role_id) DO NOTHING;
        """
    )

    # Add back step_email.sender_account_id
    op.add_column(
        "step_email",
        sa.Column("sender_account_id", sa.UUID(as_uuid=False), nullable=True),
    )
    op.create_foreign_key(
        "fk_step_email_sender_account_id_sender_account",
        "step_email",
        "sender_account",
        ["sender_account_id"],
        ["account_id"],
        ondelete="SET NULL",
    )

    # Remove collaborator.role_id
    op.drop_constraint("fk_collaborator_role_id_role", "collaborator", type_="foreignkey")
    op.drop_column("collaborator", "role_id")

    # Drop campaign sender pool
    op.drop_table("campaign_sender_pool")
