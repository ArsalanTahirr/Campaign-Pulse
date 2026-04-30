"""add scheduling locks and advanced constraints

Revision ID: 0ff55274753b
Revises: 5f1c3b7a9e10
Create Date: 2026-04-27 00:31:18.916958

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0ff55274753b'
down_revision: Union[str, None] = '5f1c3b7a9e10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint('uq_campaign_workspace_name', 'campaign', ['workspace_id', 'campaign_name'])
    op.create_index('uq_campaign_workspace_name_lower', 'campaign', ['workspace_id', sa.literal_column('lower(campaign_name)')], unique=True)
    op.alter_column(
        'campaign',
        'timezone',
        existing_type=sa.String(length=100),
        nullable=False,
        server_default=sa.text("'UTC'"),
    )
    op.create_check_constraint(
        'ck_campaign_timezone_not_blank',
        'campaign',
        "timezone <> ''",
    )
    op.create_check_constraint(
        'ck_campaign_status',
        'campaign',
        "status IN ('draft','scheduled','active','paused','completed','archived','deleted')",
    )
    op.add_column('lead', sa.Column('next_scheduled_at', postgresql.TIMESTAMP(timezone=True), nullable=True, comment='UTC timestamp when the next step email should fire for this lead.'))
    op.add_column('lead', sa.Column('delivery_state', sa.String(length=20), server_default=sa.text("'queued'"), nullable=False, comment='Worker state: queued | sending | sent | failed | paused.'))
    op.add_column('lead', sa.Column('locked_at', postgresql.TIMESTAMP(timezone=True), nullable=True, comment='UTC timestamp when a worker claimed this lead for sending.'))
    op.add_column('lead', sa.Column('lock_token', sa.UUID(as_uuid=False), nullable=True, comment='Worker claim token used to prevent duplicate sends across workers.'))
    op.create_check_constraint(
        'ck_lead_status',
        'lead',
        "lead_status IN ('active','replied','unsubscribed','bounced','completed')",
    )
    op.create_check_constraint(
        'ck_lead_delivery_state',
        'lead',
        "delivery_state IN ('queued','sending','sent','failed','paused')",
    )
    op.create_index('ix_lead_campaign_next_scheduled', 'lead', ['campaign_id', 'next_scheduled_at'], unique=False)
    op.create_index('ix_lead_next_scheduled_state', 'lead', ['next_scheduled_at', 'delivery_state'], unique=False)
    op.add_column('step_email', sa.Column('content_hash', sa.String(length=64), nullable=True, comment='SHA-256 hash of normalized subject+body for duplicate-content checks.'))
    op.create_index('ix_step_email_content_hash', 'step_email', ['content_hash'], unique=False)
    op.create_index('ix_step_email_step_content_hash', 'step_email', ['step_id', 'content_hash'], unique=False)

    # Auto-compute content hash for spam-similarity checks.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_step_email_set_content_hash()
        RETURNS trigger AS $$
        BEGIN
            NEW.content_hash := encode(
                digest(
                    COALESCE(lower(trim(NEW.subject_line)), '') || '|' || COALESCE(trim(NEW.email_body), ''),
                    'sha256'
                ),
                'hex'
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_step_email_set_content_hash
        BEFORE INSERT OR UPDATE OF subject_line, email_body
        ON step_email
        FOR EACH ROW
        EXECUTE FUNCTION fn_step_email_set_content_hash();
        """
    )
    op.execute(
        """
        UPDATE step_email
        SET content_hash = encode(
            digest(
                COALESCE(lower(trim(subject_line)), '') || '|' || COALESCE(trim(email_body), ''),
                'sha256'
            ),
            'hex'
        )
        WHERE content_hash IS NULL;
        """
    )

    # Soft delete campaigns: DELETE becomes status='deleted' + updated_at.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_campaign_soft_delete()
        RETURNS trigger AS $$
        BEGIN
            UPDATE campaign
            SET status = 'deleted',
                updated_at = now()
            WHERE campaign_id = OLD.campaign_id;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_campaign_soft_delete
        BEFORE DELETE ON campaign
        FOR EACH ROW
        EXECUTE FUNCTION fn_campaign_soft_delete();
        """
    )

    # Guard rails for sequence/lead edits based on campaign status.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_guard_sequence_step_mutation()
        RETURNS trigger AS $$
        DECLARE
            v_campaign_id uuid;
            v_status text;
        BEGIN
            v_campaign_id := COALESCE(NEW.campaign_id, OLD.campaign_id);
            SELECT status INTO v_status FROM campaign WHERE campaign_id = v_campaign_id;

            IF v_status = 'completed' THEN
                RAISE EXCEPTION 'Cannot modify sequence steps for completed campaigns';
            END IF;

            IF v_status NOT IN ('draft', 'paused') THEN
                RAISE EXCEPTION 'Sequence steps can only be edited when campaign is draft or paused';
            END IF;
            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_guard_sequence_step_mutation
        BEFORE INSERT OR UPDATE OR DELETE ON sequence_step
        FOR EACH ROW
        EXECUTE FUNCTION fn_guard_sequence_step_mutation();
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_guard_step_email_mutation()
        RETURNS trigger AS $$
        DECLARE
            v_step_id uuid;
            v_status text;
        BEGIN
            v_step_id := COALESCE(NEW.step_id, OLD.step_id);
            SELECT c.status
              INTO v_status
              FROM sequence_step s
              JOIN campaign c ON c.campaign_id = s.campaign_id
             WHERE s.step_id = v_step_id;

            IF v_status = 'completed' THEN
                RAISE EXCEPTION 'Cannot modify step emails for completed campaigns';
            END IF;

            IF v_status NOT IN ('draft', 'paused') THEN
                RAISE EXCEPTION 'Step emails can only be edited when campaign is draft or paused';
            END IF;
            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_guard_step_email_mutation
        BEFORE INSERT OR UPDATE OR DELETE ON step_email
        FOR EACH ROW
        EXECUTE FUNCTION fn_guard_step_email_mutation();
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_guard_lead_mutation_on_completed()
        RETURNS trigger AS $$
        DECLARE
            v_campaign_id uuid;
            v_status text;
        BEGIN
            v_campaign_id := COALESCE(NEW.campaign_id, OLD.campaign_id);
            SELECT status INTO v_status FROM campaign WHERE campaign_id = v_campaign_id;
            IF v_status = 'completed' THEN
                RAISE EXCEPTION 'Cannot modify leads for completed campaigns';
            END IF;
            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_guard_lead_mutation_on_completed
        BEFORE INSERT OR UPDATE OR DELETE ON lead
        FOR EACH ROW
        EXECUTE FUNCTION fn_guard_lead_mutation_on_completed();
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS trg_guard_lead_mutation_on_completed ON lead")
    op.execute("DROP FUNCTION IF EXISTS fn_guard_lead_mutation_on_completed()")
    op.execute("DROP TRIGGER IF EXISTS trg_guard_step_email_mutation ON step_email")
    op.execute("DROP FUNCTION IF EXISTS fn_guard_step_email_mutation()")
    op.execute("DROP TRIGGER IF EXISTS trg_guard_sequence_step_mutation ON sequence_step")
    op.execute("DROP FUNCTION IF EXISTS fn_guard_sequence_step_mutation()")
    op.execute("DROP TRIGGER IF EXISTS trg_campaign_soft_delete ON campaign")
    op.execute("DROP FUNCTION IF EXISTS fn_campaign_soft_delete()")
    op.execute("DROP TRIGGER IF EXISTS trg_step_email_set_content_hash ON step_email")
    op.execute("DROP FUNCTION IF EXISTS fn_step_email_set_content_hash()")

    op.drop_index('ix_step_email_step_content_hash', table_name='step_email')
    op.drop_index('ix_step_email_content_hash', table_name='step_email')
    op.drop_column('step_email', 'content_hash')
    op.drop_index('ix_lead_next_scheduled_state', table_name='lead')
    op.drop_index('ix_lead_campaign_next_scheduled', table_name='lead')
    op.drop_constraint('ck_lead_delivery_state', 'lead', type_='check')
    op.drop_constraint('ck_lead_status', 'lead', type_='check')
    op.drop_column('lead', 'lock_token')
    op.drop_column('lead', 'locked_at')
    op.drop_column('lead', 'delivery_state')
    op.drop_column('lead', 'next_scheduled_at')
    op.drop_constraint('ck_campaign_status', 'campaign', type_='check')
    op.drop_constraint('ck_campaign_timezone_not_blank', 'campaign', type_='check')
    op.alter_column(
        'campaign',
        'timezone',
        existing_type=sa.String(length=100),
        nullable=False,
        server_default=sa.text("'UTC'"),
    )
    op.drop_index('uq_campaign_workspace_name_lower', table_name='campaign')
    op.drop_constraint('uq_campaign_workspace_name', 'campaign', type_='unique')
