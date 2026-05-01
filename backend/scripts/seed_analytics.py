#!/usr/bin/env python3
"""
scripts/seed_analytics.py — Seed script for local analytics testing.

Creates fake campaigns, sender accounts, leads, and engagement events so the
analytics dashboard can be visually verified with realistic-looking data.

Usage (from the backend/ directory):
    python scripts/seed_analytics.py            # insert seed data
    python scripts/seed_analytics.py --cleanup  # delete all seed data

All seed objects are tagged with the "[TEST]" prefix so they can be identified
and deleted without touching any real workspace data.

SAFETY: The script refuses to run when NODE_ENV=production or when DATABASE_URL
contains the substring "prod" (override with ALLOW_SEED_IN_PROD=true).
"""

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap — allow `from app.xxx import` when run from any directory
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

# ---------------------------------------------------------------------------
# Load .env before importing any app module that reads env vars
# ---------------------------------------------------------------------------
from dotenv import load_dotenv  # noqa: E402

load_dotenv(dotenv_path=_BACKEND_DIR.parent / ".env")

# ---------------------------------------------------------------------------
# Production safety guard
# ---------------------------------------------------------------------------
if os.environ.get("NODE_ENV") == "production":
    print("ERROR: Seed script cannot run in production.")
    sys.exit(1)

_DB_URL: str = os.environ.get("DATABASE_URL", "")
if not _DB_URL:
    print("ERROR: DATABASE_URL is not set.")
    sys.exit(1)

if "prod" in _DB_URL.lower() and os.environ.get("ALLOW_SEED_IN_PROD") != "true":
    print("ERROR: DATABASE_URL appears to point at a production database.")
    print("       Set ALLOW_SEED_IN_PROD=true to override (not recommended).")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Late imports (after env is loaded)
# ---------------------------------------------------------------------------
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.auth import hash_password  # noqa: E402
from app.models import (  # noqa: E402
    Campaign,
    CampaignSenderPool,
    Collaborator,
    EmailEvent,
    Lead,
    LocalAuth,
    Role,
    SenderAccount,
    SequenceStep,
    User,
    Workspace,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SEED_TAG = "[TEST]"
SEED_EMAIL_DOMAIN = "campaignpulse-seed.dev"
SEED_WORKSPACE_NAME = f"{SEED_TAG} Seed Workspace"
SEED_USER_EMAIL = f"seed-admin@{SEED_EMAIL_DOMAIN}"

CAMPAIGNS_CONFIG = [
    {"suffix": "Q2 Active Outreach",    "status": "active"},
    {"suffix": "Q1 Completed Campaign", "status": "completed"},
]

SENDER_EMAILS = [
    f"sender-alpha@{SEED_EMAIL_DOMAIN}",
    f"sender-beta@{SEED_EMAIL_DOMAIN}",
    f"sender-gamma@{SEED_EMAIL_DOMAIN}",
]

LEADS_PER_CAMPAIGN = 50
DAYS_BACK = 30

# Exact lead counts per engagement type (deterministic — no randomness needed).
# Rates across the whole workspace (2 campaigns × 50 leads = 100 delivered):
#   Opens:        30 / 50 per campaign = 60.00 %
#   Clicks:       13 / 50 per campaign = 26.00 %
#   Replies:       8 / 50 per campaign = 16.00 %
#   Opportunities: 3 / 50 per campaign =  6.00 %
N_OPEN = 30
N_CLICK = 13
N_REPLY = 8
N_OPP = 3  # subset of replies (all 3 also reply)

# ---------------------------------------------------------------------------
# DB setup
# ---------------------------------------------------------------------------
_engine = create_engine(_DB_URL, pool_pre_ping=True)
_Session = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid() -> str:
    return str(uuid.uuid4())


def _get_or_create_role(db, name: str) -> Role:
    role = db.query(Role).filter(Role.role_name == name).first()
    if not role:
        role = Role(role_id=_uid(), role_name=name, permissions={})
        db.add(role)
        db.flush()
    return role


def _make_event(
    lead_id: str,
    step_id: str,
    event_type: str,
    sender_account_id: str,
    occurred_at: datetime,
) -> EmailEvent:
    return EmailEvent(
        event_id=_uid(),
        lead_id=lead_id,
        step_id=step_id,
        event_type=event_type,
        event_scope="lead",
        sender_account_id=sender_account_id,
        occurred_at=occurred_at,
    )


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

def seed() -> None:
    db = _Session()
    try:
        # ── Idempotency check ────────────────────────────────────────────────
        existing = (
            db.query(Workspace)
            .filter(Workspace.workspace_name == SEED_WORKSPACE_NAME)
            .first()
        )
        if existing:
            print(f"\nSeed data already exists  (workspace: '{SEED_WORKSPACE_NAME}').")
            print("Run with --cleanup first, then re-run to refresh.\n")
            return

        now = datetime.now(timezone.utc)

        # ── Seed user ────────────────────────────────────────────────────────
        seed_user = db.query(User).filter(User.email == SEED_USER_EMAIL).first()
        if not seed_user:
            seed_user = User(
                user_id=_uid(),
                email=SEED_USER_EMAIL,
                first_name="Seed",
                last_name="Admin",
                is_verified=True,
            )
            db.add(seed_user)
            db.add(LocalAuth(
                user_id=seed_user.user_id,
                password_hash=hash_password("SeedPass123!"),
            ))
            db.flush()

        # ── Workspace ────────────────────────────────────────────────────────
        ws = Workspace(workspace_id=_uid(), workspace_name=SEED_WORKSPACE_NAME)
        db.add(ws)
        db.flush()

        owner_role = _get_or_create_role(db, "Owner")
        db.add(Collaborator(
            member_id=_uid(),
            workspace_id=ws.workspace_id,
            user_id=seed_user.user_id,
            role_id=owner_role.role_id,
            invite_status="accepted",
        ))
        db.flush()

        # ── Sender accounts ──────────────────────────────────────────────────
        senders: list[SenderAccount] = []
        for email in SENDER_EMAILS:
            sa = SenderAccount(
                account_id=_uid(),
                workspace_id=ws.workspace_id,
                provider_type="smtp",
                email=email,
                status="active",
                is_verified=True,
            )
            db.add(sa)
            senders.append(sa)
        db.flush()

        # ── Counters for the summary ─────────────────────────────────────────
        total_sent = total_open = total_click = total_reply = total_opps = 0

        # ── Campaigns ────────────────────────────────────────────────────────
        for campaign_idx, cfg in enumerate(CAMPAIGNS_CONFIG):
            campaign_name = f"{SEED_TAG} {cfg['suffix']}"

            # Create the campaign as 'draft' first so the DB trigger that
            # guards sequence_step insertion allows the INSERT.
            # The status is updated to the target value after the step is added.
            campaign = Campaign(
                campaign_id=_uid(),
                workspace_id=ws.workspace_id,
                campaign_name=campaign_name,
                status="draft",
                open_tracking_enabled=True,
            )
            db.add(campaign)
            db.flush()

            # Assign all senders to this campaign
            for sender in senders:
                db.add(CampaignSenderPool(
                    campaign_id=campaign.campaign_id,
                    sender_account_id=sender.account_id,
                ))
            db.flush()

            # Step 1 — required so sequence_started metric counts correctly.
            # Must be inserted while campaign is still 'draft' (trigger requirement).
            step1 = SequenceStep(
                step_id=_uid(),
                campaign_id=campaign.campaign_id,
                step_number=1,
                wait_days=0,
            )
            db.add(step1)
            db.flush()

            # ── Leads + events ───────────────────────────────────────────────
            # Keep campaign in 'draft' throughout lead/event insertion.
            # DB triggers block mutations on leads and steps for non-draft
            # campaigns. The target status is applied after all rows are added.
            # Pre-defined sets decide which lead indices get which events.
            # Using index slices guarantees exact, reproducible counts.
            open_set  = set(range(N_OPEN))    # leads 0-29   → 60 %
            click_set = set(range(N_CLICK))   # leads 0-12   → 26 %
            reply_set = set(range(N_REPLY))   # leads 0-7    → 16 %
            opps_set  = set(range(N_OPP))     # leads 0-2    →  6 % (subset of replies)

            for i in range(LEADS_PER_CAMPAIGN):
                # Round-robin sender assignment
                sender = senders[i % len(senders)]

                # Spread sent events evenly across the last DAYS_BACK days.
                # Lead 0 → 1 day ago, lead 1 → 2 days ago, …, lead 29 → 30 days ago,
                # lead 30 → 1 day ago (wraps), etc.
                days_ago = (i % DAYS_BACK) + 1
                sent_at = now - timedelta(days=days_ago, hours=9)

                # Use campaign-specific email prefix to keep leads unique per campaign.
                campaign_slug = f"c{campaign_idx}"
                lead = Lead(
                    lead_id=_uid(),
                    campaign_id=campaign.campaign_id,
                    email=f"lead-{campaign_slug}-{i:03d}@{SEED_EMAIL_DOMAIN}",
                    first_name="Lead",
                    last_name=f"{campaign_slug}-{i:03d}",
                    lead_status="replied" if i in reply_set else "active",
                    is_opportunity=(i in opps_set),
                )
                db.add(lead)
                db.flush()

                # sent — always (drives sequence_started and total_sent)
                db.add(_make_event(lead.lead_id, step1.step_id, "sent",    sender.account_id, sent_at))
                total_sent += 1

                # opened
                if i in open_set:
                    db.add(_make_event(lead.lead_id, step1.step_id, "opened",  sender.account_id, sent_at + timedelta(hours=2)))
                    total_open += 1

                # clicked
                if i in click_set:
                    db.add(_make_event(lead.lead_id, step1.step_id, "clicked", sender.account_id, sent_at + timedelta(hours=2, minutes=15)))
                    total_click += 1

                # replied
                if i in reply_set:
                    db.add(_make_event(lead.lead_id, step1.step_id, "replied", sender.account_id, sent_at + timedelta(hours=4)))
                    total_reply += 1

                if i in opps_set:
                    total_opps += 1

            db.flush()

            # All leads and events are in — now update to the real target status.
            campaign.status = cfg["status"]
            db.flush()

        db.commit()

        # ── Console summary ──────────────────────────────────────────────────
        total_delivered = total_sent  # no bounces seeded
        n_campaigns = len(CAMPAIGNS_CONFIG)

        print("\nSeed complete.")
        print("-" * 47)
        print(f"  Workspace:             {SEED_WORKSPACE_NAME}")
        print(f"  Campaigns created:     {n_campaigns}")
        print(f"  Sending accounts:      {len(SENDER_EMAILS)}")
        print(f"  Leads seeded:          {LEADS_PER_CAMPAIGN * n_campaigns}")
        print(f"  Emails sent:           {total_sent}")
        print(f"  Opens recorded:        {total_open}")
        print(f"  Clicks recorded:       {total_click}")
        print(f"  Replies recorded:      {total_reply}")
        print(f"  Opportunities flagged: {total_opps}")
        print("-" * 47)
        if total_delivered > 0:
            print(f"  Expected Open Rate:    {total_open  / total_delivered * 100:.2f}%")
            print(f"  Expected Click Rate:   {total_click / total_delivered * 100:.2f}%")
            print(f"  Expected Reply Rate:   {total_reply / total_delivered * 100:.2f}%")
        print("-" * 47)
        print("\n  Open the analytics dashboard to verify the data.")
        print("  Run with --cleanup to remove all seed records.\n")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def cleanup() -> None:
    """
    Delete all seed data in FK-safe order using raw SQL.

    The database has several BEFORE DELETE triggers that block or soft-intercept
    deletions (trg_campaign_soft_delete, trg_guard_lead_mutation_on_completed,
    trg_guard_sequence_step_mutation). These are temporarily disabled for the
    duration of the cleanup transaction and re-enabled immediately after.
    ALTER TABLE ... DISABLE/ENABLE TRIGGER is transactional in PostgreSQL — if
    the transaction rolls back the triggers are automatically restored.
    """
    from sqlalchemy import text

    # Triggers to temporarily suspend during cleanup.
    _TRIGGERS = [
        ("campaign",       "trg_campaign_soft_delete"),
        ("lead",           "trg_guard_lead_mutation_on_completed"),
        ("sequence_step",  "trg_guard_sequence_step_mutation"),
    ]

    db = _Session()
    try:
        row = db.execute(
            text("SELECT workspace_id::text, workspace_name FROM workspace WHERE workspace_name = :name"),
            {"name": SEED_WORKSPACE_NAME},
        ).fetchone()

        if not row:
            print("\nNo seed data found. Nothing to clean up.\n")
            return

        ws_id: str = row[0]
        ws_name: str = row[1]

        # ── Suspend blocking triggers ────────────────────────────────────────
        for table, trigger in _TRIGGERS:
            db.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER {trigger}"))

        # ── Collect campaign IDs (UUIDs are safe to interpolate) ─────────────
        cid_rows = db.execute(
            text("SELECT campaign_id::text FROM campaign WHERE workspace_id = :ws_id"),
            {"ws_id": ws_id},
        ).fetchall()
        campaign_ids = [str(r[0]) for r in cid_rows]

        if campaign_ids:
            cid_literal = ", ".join(f"'{c}'" for c in campaign_ids)

            # Delete children in FK order, innermost first.
            db.execute(text(f"""
                DELETE FROM email_event
                WHERE lead_id IN (
                    SELECT lead_id FROM lead WHERE campaign_id IN ({cid_literal})
                )
            """))
            db.execute(text(f"DELETE FROM lead          WHERE campaign_id IN ({cid_literal})"))
            db.execute(text(f"DELETE FROM sequence_step WHERE campaign_id IN ({cid_literal})"))
            db.execute(text(f"DELETE FROM campaign_sender_pool WHERE campaign_id IN ({cid_literal})"))
            db.execute(text(f"DELETE FROM campaign      WHERE campaign_id IN ({cid_literal})"))

        # Warmup settings reference sender_account (FK), delete first.
        db.execute(text("""
            DELETE FROM warmup_settings
            WHERE account_id IN (
                SELECT account_id FROM sender_account WHERE workspace_id = :ws_id
            )
        """), {"ws_id": ws_id})

        db.execute(text("DELETE FROM sender_account WHERE workspace_id = :ws_id"), {"ws_id": ws_id})
        db.execute(text("DELETE FROM collaborator    WHERE workspace_id = :ws_id"), {"ws_id": ws_id})
        db.execute(text("DELETE FROM workspace       WHERE workspace_id = :ws_id"), {"ws_id": ws_id})

        # Delete seed user (cascades to local_auth, oauth_accounts, refresh_tokens).
        db.execute(text("DELETE FROM users WHERE email = :email"), {"email": SEED_USER_EMAIL})

        # ── Re-enable triggers ───────────────────────────────────────────────
        for table, trigger in _TRIGGERS:
            db.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER {trigger}"))

        db.commit()
        print(f"\nCleanup complete.")
        print(f"Removed '{ws_name}' and all associated seed data.\n")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if "--cleanup" in sys.argv:
        cleanup()
    else:
        seed()
