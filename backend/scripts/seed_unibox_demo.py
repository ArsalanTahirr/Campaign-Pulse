#!/usr/bin/env python3
"""
scripts/seed_unibox_demo.py — Realistic demo dataset for Unibox end-to-end testing.

Creates a fully-wired demo environment:
  • 1 workspace  (Acme Growth Agency)
  • 1 demo user  (demo@acmegrowthagency.com / DemoPass123!)
  • 3 sender accounts / inboxes
  • 3 campaigns with sequences
  • 8 leads (cold, warm, engaged, won)
  • 8 conversation threads with proper RFC 2822 threading headers
  • 3 orphan email threads (unknown senders)
  • Realistic read/unread states
  • Full-text search vector populated for every message

Usage (run from the backend/ directory):
    python scripts/seed_unibox_demo.py            # insert demo data
    python scripts/seed_unibox_demo.py --cleanup  # remove all demo data

IDEMPOTENCY: Detected by the workspace name "[DEMO] Acme Growth Agency".
Running the script twice is safe — it skips creation if the workspace exists.

SAFETY: Refuses to run if DATABASE_URL contains "prod" (override with
ALLOW_SEED_IN_PROD=true).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEMO LOGIN
  Email:    demo@acmegrowthagency.com
  Password: DemoPass123!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(dotenv_path=_BACKEND_DIR.parent / ".env")

# ---------------------------------------------------------------------------
# Safety guard
# ---------------------------------------------------------------------------
_DB_URL: str = os.environ.get("DATABASE_URL", "")
if not _DB_URL:
    print("ERROR: DATABASE_URL is not set in .env")
    sys.exit(1)

if "prod" in _DB_URL.lower() and os.environ.get("ALLOW_SEED_IN_PROD") != "true":
    print("ERROR: DATABASE_URL appears to point at a production database.")
    print("       Set ALLOW_SEED_IN_PROD=true to override.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Late imports
# ---------------------------------------------------------------------------
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker, Session  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.auth import hash_password  # noqa: E402
from app.models import (  # noqa: E402
    Campaign,
    CampaignSenderPool,
    Collaborator,
    Lead,
    LocalAuth,
    Role,
    SenderAccount,
    SequenceStep,
    StepEmail,
    UniboxMessage,
    UniboxThread,
    User,
    Workspace,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEMO_WORKSPACE_NAME = "[DEMO] Acme Growth Agency"
DEMO_USER_EMAIL     = "demo@acmegrowthagency.com"
DEMO_USER_PASSWORD  = "DemoPass123!"

NOW = datetime.now(timezone.utc)

def _ago(days: int = 0, hours: int = 0, minutes: int = 0) -> datetime:
    return NOW - timedelta(days=days, hours=hours, minutes=minutes)


# ===========================================================================
# Database session
# ===========================================================================
engine = create_engine(_DB_URL, poolclass=NullPool)
SessionLocal = sessionmaker(bind=engine)


# ===========================================================================
# Helpers
# ===========================================================================

def _new_id() -> str:
    return str(uuid.uuid4())


def _mid(local: str) -> str:
    """Build a deterministic-looking RFC 2822 Message-ID."""
    return f"<{local}@acmegrowthagency.com>"


def _tsv(content: str, db: Session) -> object:
    """Compute a PostgreSQL tsvector for full-text search."""
    return db.execute(
        text("SELECT to_tsvector('english', :c)"),
        {"c": content},
    ).scalar()


def _refs(ids: list[str]) -> str:
    """Build References header from a list of Message-IDs."""
    return " ".join(ids)


def _make_message(
    *,
    db: Session,
    thread: UniboxThread,
    sender_account: SenderAccount,
    direction: str,
    mid: str,
    in_reply_to: Optional[str],
    references: Optional[str],
    from_addr: str,
    to_addrs: list[str],
    subject: str,
    body_text: str,
    is_read: bool,
    status: str,
    lead: Optional[Lead] = None,
    ts: Optional[datetime] = None,
) -> UniboxMessage:
    if ts is None:
        ts = NOW
    msg = UniboxMessage(
        message_id=_new_id(),
        thread_id=thread.thread_id,
        sender_account_id=sender_account.account_id,
        lead_id=lead.lead_id if lead else None,
        direction=direction,
        message_id_header=mid,
        in_reply_to=in_reply_to,
        references_header=references,
        from_address=from_addr,
        to_addresses=to_addrs,
        subject=subject,
        body_text=body_text,
        is_read=is_read,
        is_orphan=(lead is None),
        status=status,
        received_at=ts if direction == "inbound" else None,
        sent_at=ts if direction == "outbound" else None,
        search_vector=_tsv(subject + " " + body_text + " " + from_addr, db),
    )
    db.add(msg)
    return msg


# ===========================================================================
# Cleanup
# ===========================================================================

def cleanup(db: Session) -> None:
    ws = db.query(Workspace).filter(Workspace.workspace_name == DEMO_WORKSPACE_NAME).first()
    user = db.query(User).filter(User.email == DEMO_USER_EMAIL).first()

    if not ws and not user:
        print("No demo data found — nothing to clean up.")
        return

    print(f"Removing demo workspace: {DEMO_WORKSPACE_NAME}")

    conn = db.connection()
    # Disable all triggers for this session so we can delete in any order
    conn.execute(text("SET session_replication_role = replica"))

    try:
        wid = ws.workspace_id if ws else None

        if wid:
            # Deepest dependants first
            conn.execute(text(
                "DELETE FROM unibox_message WHERE thread_id IN "
                "(SELECT thread_id FROM unibox_thread WHERE workspace_id = :wid)"
            ), {"wid": wid})
            conn.execute(text("DELETE FROM unibox_thread WHERE workspace_id = :wid"), {"wid": wid})
            conn.execute(text(
                "DELETE FROM email_event WHERE lead_id IN "
                "(SELECT lead_id FROM lead WHERE campaign_id IN "
                " (SELECT campaign_id FROM campaign WHERE workspace_id = :wid))"
            ), {"wid": wid})
            conn.execute(text(
                "DELETE FROM step_email WHERE step_id IN "
                "(SELECT step_id FROM sequence_step WHERE campaign_id IN "
                " (SELECT campaign_id FROM campaign WHERE workspace_id = :wid))"
            ), {"wid": wid})
            conn.execute(text(
                "DELETE FROM sequence_step WHERE campaign_id IN "
                "(SELECT campaign_id FROM campaign WHERE workspace_id = :wid)"
            ), {"wid": wid})
            conn.execute(text(
                "DELETE FROM campaign_sender_pool WHERE campaign_id IN "
                "(SELECT campaign_id FROM campaign WHERE workspace_id = :wid)"
            ), {"wid": wid})
            conn.execute(text("DELETE FROM lead WHERE campaign_id IN (SELECT campaign_id FROM campaign WHERE workspace_id = :wid)"), {"wid": wid})
            conn.execute(text("DELETE FROM campaign WHERE workspace_id = :wid"), {"wid": wid})
            conn.execute(text("DELETE FROM sender_account WHERE workspace_id = :wid"), {"wid": wid})
            conn.execute(text("DELETE FROM collaborator WHERE workspace_id = :wid"), {"wid": wid})
            conn.execute(text("DELETE FROM workspace WHERE workspace_id = :wid"), {"wid": wid})

        if user:
            uid = user.user_id
            conn.execute(text("DELETE FROM local_auth WHERE user_id = :uid"), {"uid": uid})
            conn.execute(text("DELETE FROM users WHERE user_id = :uid"), {"uid": uid})

        conn.execute(text("SET session_replication_role = DEFAULT"))
        db.commit()
        print("[OK] Demo data removed.")


# ===========================================================================
# Seed
# ===========================================================================

def seed(db: Session) -> None:

    # ── Idempotency check ──────────────────────────────────────────────────
    existing = db.query(Workspace).filter(Workspace.workspace_name == DEMO_WORKSPACE_NAME).first()
    if existing:
        print("Demo data already exists. Run with --cleanup first to re-seed.")
        return

    print("Seeding Unibox demo data …")

    # ── Demo user ──────────────────────────────────────────────────────────
    user = User(
        user_id=_new_id(),
        email=DEMO_USER_EMAIL,
        first_name="Demo",
        last_name="Admin",
        is_verified=True,
    )
    db.add(user)
    db.flush()

    db.add(LocalAuth(
        user_id=user.user_id,
        password_hash=hash_password(DEMO_USER_PASSWORD),
        verification_token=None,
    ))

    # ── Workspace ──────────────────────────────────────────────────────────
    ws = Workspace(
        workspace_id=_new_id(),
        workspace_name=DEMO_WORKSPACE_NAME,
    )
    db.add(ws)
    db.flush()

    # ── Role + Collaborator ────────────────────────────────────────────────
    owner_role = db.query(Role).filter(Role.role_name == "Owner").first()
    if not owner_role:
        owner_role = Role(
            role_id=_new_id(),
            role_name="Owner",
            permissions={},
        )
        db.add(owner_role)
        db.flush()

    db.add(Collaborator(
        member_id=_new_id(),
        workspace_id=ws.workspace_id,
        user_id=user.user_id,
        role_id=owner_role.role_id,
        invite_status="accepted",
    ))
    db.flush()

    # ── Sender accounts (inboxes) ──────────────────────────────────────────
    inbox_john = SenderAccount(
        account_id=_new_id(),
        workspace_id=ws.workspace_id,
        provider_type="smtp",
        email="john@acmegrowthagency.com",
        status="active",
        is_verified=True,
        daily_sending_limit=150,
    )
    inbox_outreach = SenderAccount(
        account_id=_new_id(),
        workspace_id=ws.workspace_id,
        provider_type="smtp",
        email="outreach@acmegrowthagency.com",
        status="active",
        is_verified=True,
        daily_sending_limit=200,
    )
    inbox_support = SenderAccount(
        account_id=_new_id(),
        workspace_id=ws.workspace_id,
        provider_type="smtp",
        email="support@acmegrowthagency.com",
        status="active",
        is_verified=True,
        daily_sending_limit=100,
    )
    db.add_all([inbox_john, inbox_outreach, inbox_support])
    db.flush()

    # ── Campaigns ──────────────────────────────────────────────────────────
    # Campaigns start as 'draft' so the DB trigger allows sequence step insertion.
    # We flip them to 'active' after steps are added.
    camp_ai = Campaign(
        campaign_id=_new_id(),
        workspace_id=ws.workspace_id,
        created_by=None,
        campaign_name="AI Outreach Q1",
        status="draft",
        open_tracking_enabled=True,
    )
    camp_startup = Campaign(
        campaign_id=_new_id(),
        workspace_id=ws.workspace_id,
        created_by=None,
        campaign_name="Startup Lead Generation",
        status="draft",
        open_tracking_enabled=True,
    )
    camp_demo = Campaign(
        campaign_id=_new_id(),
        workspace_id=ws.workspace_id,
        created_by=None,
        campaign_name="Product Demo Follow-ups",
        status="draft",
        open_tracking_enabled=True,
    )
    db.add_all([camp_ai, camp_startup, camp_demo])
    db.flush()

    # Link sender accounts to campaigns
    for camp in [camp_ai, camp_startup, camp_demo]:
        db.add(CampaignSenderPool(campaign_id=camp.campaign_id, sender_account_id=inbox_john.account_id))
        db.add(CampaignSenderPool(campaign_id=camp.campaign_id, sender_account_id=inbox_outreach.account_id))
    db.add(CampaignSenderPool(campaign_id=camp_demo.campaign_id, sender_account_id=inbox_support.account_id))

    # Add a sequence step to each campaign (trigger only blocks edits on active/running)
    for camp in [camp_ai, camp_startup, camp_demo]:
        step = SequenceStep(
            step_id=_new_id(),
            campaign_id=camp.campaign_id,
            step_number=1,
            wait_days=0,
            send_time="09:00",
            send_window_end="17:00",
            send_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        )
        db.add(step)
        db.flush()
        db.add(StepEmail(
            email_id=_new_id(),
            step_id=step.step_id,
            subject_line="{{first_name}}, quick question about {{company}}",
            email_body="<p>Hi {{first_name}},<br><br>I noticed {{company}} is scaling fast...</p>",
        ))

    db.flush()

    # Now promote campaigns to active (trigger only guards sequence step mutations)
    camp_ai.status = "active"
    camp_startup.status = "active"
    camp_demo.status = "active"
    db.flush()

    # ── Leads ──────────────────────────────────────────────────────────────
    def _lead(campaign_id, email, first, last, company, status="replied", pipe="lead", delivery="paused"):
        l = Lead(
            lead_id=_new_id(),
            campaign_id=campaign_id,
            email=email,
            first_name=first,
            last_name=last,
            lead_status=status,
            pipeline_status=pipe,
            delivery_state=delivery,
            is_opportunity=pipe in ("meeting-booked", "meeting-completed", "won"),
        )
        db.add(l)
        db.flush()
        return l

    sarah  = _lead(camp_ai.campaign_id,     "sarah.chen@techvision-ai.com",    "Sarah",  "Chen",      "TechVision AI",        pipe="meeting-booked")
    marcus = _lead(camp_ai.campaign_id,     "marcus.webb@dataflow.io",          "Marcus", "Webb",      "DataFlow Systems",     pipe="lead",         status="active", delivery="queued")
    jordan = _lead(camp_ai.campaign_id,     "jordan.kim@nexgenai.co",           "Jordan", "Kim",       "NexGenAI",             pipe="interested")
    priya  = _lead(camp_startup.campaign_id,"priya.sharma@launchpad.vc",        "Priya",  "Sharma",    "LaunchPad Ventures",   pipe="interested")
    alex   = _lead(camp_startup.campaign_id,"alex.rodriguez@scaleup.io",        "Alex",   "Rodriguez", "ScaleUp Inc",          pipe="lead",         status="active", delivery="queued")
    emma   = _lead(camp_demo.campaign_id,   "emma.thompson@innovateco.com",     "Emma",   "Thompson",  "InnovateCo",           pipe="meeting-completed")
    david  = _lead(camp_demo.campaign_id,   "david.park@growthbridge.co",       "David",  "Park",      "GrowthBridge",         pipe="won")
    lily   = _lead(camp_demo.campaign_id,   "lily.wang@connecthub.io",          "Lily",   "Wang",      "ConnectHub",           pipe="interested")

    db.flush()

    # ===========================================================================
    # THREADS
    # ===========================================================================

    # ───────────────────────────────────────────────────────────────────────────
    # THREAD 1 — Active | AI Outreach | john@acme | Sarah Chen | meeting-booked
    # ───────────────────────────────────────────────────────────────────────────
    t1 = UniboxThread(
        thread_id=_new_id(),
        workspace_id=ws.workspace_id,
        lead_id=sarah.lead_id,
        campaign_id=camp_ai.campaign_id,
        subject="AI Integration Opportunity for TechVision AI",
        last_message_at=_ago(hours=3),
        is_orphan=False,
    )
    db.add(t1); db.flush()

    m1_1_id = _mid("t1-m1")
    m1_2_id = _mid("t1-m2")
    m1_3_id = _mid("t1-m3")
    m1_4_id = _mid("t1-m4")
    m1_5_id = _mid("t1-m5")

    _make_message(db=db, thread=t1, sender_account=inbox_john, direction="outbound",
        mid=m1_1_id, in_reply_to=None, references=None,
        from_addr="john@acmegrowthagency.com", to_addrs=["sarah.chen@techvision-ai.com"],
        subject="AI Integration Opportunity for TechVision AI", is_read=True, status="sent",
        lead=sarah, ts=_ago(days=7),
        body_text=(
            "Hi Sarah,\n\nI came across TechVision AI's recent Series B announcement — "
            "congratulations on the milestone!\n\nWe help AI-first companies like yours streamline "
            "their sales outreach with intelligent sequencing and full-funnel analytics. I'd love to "
            "show you how teams like DataFlow and NexGenAI are booking 3x more demos using our "
            "platform.\n\nWould a quick 20-minute demo make sense this week?\n\nBest,\nJohn\n"
            "Acme Growth Agency"
        ),
    )
    _make_message(db=db, thread=t1, sender_account=inbox_john, direction="inbound",
        mid=m1_2_id, in_reply_to=m1_1_id, references=_refs([m1_1_id]),
        from_addr="sarah.chen@techvision-ai.com", to_addrs=["john@acmegrowthagency.com"],
        subject="Re: AI Integration Opportunity for TechVision AI", is_read=True, status="received",
        lead=sarah, ts=_ago(days=6),
        body_text=(
            "Hi John,\n\nThanks for reaching out. The timing is actually great — we're evaluating "
            "a few outreach tools for Q2.\n\nCould you share more details on your pricing? "
            "We're a team of 35, mostly in sales and growth.\n\nBest,\nSarah"
        ),
    )
    _make_message(db=db, thread=t1, sender_account=inbox_john, direction="outbound",
        mid=m1_3_id, in_reply_to=m1_2_id, references=_refs([m1_1_id, m1_2_id]),
        from_addr="john@acmegrowthagency.com", to_addrs=["sarah.chen@techvision-ai.com"],
        subject="Re: AI Integration Opportunity for TechVision AI", is_read=True, status="sent",
        lead=sarah, ts=_ago(days=5),
        body_text=(
            "Hi Sarah,\n\nGreat to hear the timing works out!\n\n"
            "Our pricing starts at $299/month for teams up to 20 seats, with enterprise plans "
            "available for 35+. I've attached a full pricing breakdown.\n\n"
            "I'd love to set up a demo so you can see the follow-up automation in action. "
            "We usually find that a 30-minute session is all it takes to understand the value.\n\n"
            "Does Thursday or Friday work for you?\n\nBest,\nJohn"
        ),
    )
    _make_message(db=db, thread=t1, sender_account=inbox_john, direction="inbound",
        mid=m1_4_id, in_reply_to=m1_3_id, references=_refs([m1_1_id, m1_2_id, m1_3_id]),
        from_addr="sarah.chen@techvision-ai.com", to_addrs=["john@acmegrowthagency.com"],
        subject="Re: AI Integration Opportunity for TechVision AI", is_read=True, status="received",
        lead=sarah, ts=_ago(days=4),
        body_text=(
            "John,\n\nFriday at 2pm PST works perfectly. Looking forward to the demo!\n\n"
            "Sarah"
        ),
    )
    _make_message(db=db, thread=t1, sender_account=inbox_john, direction="outbound",
        mid=m1_5_id, in_reply_to=m1_4_id, references=_refs([m1_1_id, m1_2_id, m1_3_id, m1_4_id]),
        from_addr="john@acmegrowthagency.com", to_addrs=["sarah.chen@techvision-ai.com"],
        subject="Re: AI Integration Opportunity for TechVision AI", is_read=False, status="sent",
        lead=sarah, ts=_ago(hours=3),
        body_text=(
            "Hi Sarah,\n\nCalendar invite sent! Our demo will cover:\n"
            "• AI-powered follow-up sequences\n"
            "• Real-time analytics and pipeline tracking\n"
            "• Partnership integrations\n\n"
            "Excited to show you what we've built. See you Friday!\n\nJohn"
        ),
    )

    # ───────────────────────────────────────────────────────────────────────────
    # THREAD 2 — Won | Product Demo Follow-ups | outreach@acme | David Park
    # ───────────────────────────────────────────────────────────────────────────
    t2 = UniboxThread(
        thread_id=_new_id(),
        workspace_id=ws.workspace_id,
        lead_id=david.lead_id,
        campaign_id=camp_demo.campaign_id,
        subject="Partnership Proposal — GrowthBridge",
        last_message_at=_ago(days=1),
        is_orphan=False,
    )
    db.add(t2); db.flush()

    m2_1_id = _mid("t2-m1")
    m2_2_id = _mid("t2-m2")
    m2_3_id = _mid("t2-m3")
    m2_4_id = _mid("t2-m4")
    m2_5_id = _mid("t2-m5")
    m2_6_id = _mid("t2-m6")

    _make_message(db=db, thread=t2, sender_account=inbox_outreach, direction="outbound",
        mid=m2_1_id, in_reply_to=None, references=None,
        from_addr="outreach@acmegrowthagency.com", to_addrs=["david.park@growthbridge.co"],
        subject="Partnership Proposal — GrowthBridge", is_read=True, status="sent",
        lead=david, ts=_ago(days=14),
        body_text=(
            "Hi David,\n\nFollowing up after our demo last Thursday — thank you for your time!\n\n"
            "As discussed, I'm attaching our partnership proposal for GrowthBridge. "
            "The key highlights:\n"
            "• Revenue share: 20% on referred customers\n"
            "• Co-marketing opportunities\n"
            "• Dedicated partnership account manager\n\n"
            "Happy to answer any questions. Looking forward to next steps!\n\n"
            "Best,\nOutreach Team\nAcme Growth Agency"
        ),
    )
    _make_message(db=db, thread=t2, sender_account=inbox_outreach, direction="inbound",
        mid=m2_2_id, in_reply_to=m2_1_id, references=_refs([m2_1_id]),
        from_addr="david.park@growthbridge.co", to_addrs=["outreach@acmegrowthagency.com"],
        subject="Re: Partnership Proposal — GrowthBridge", is_read=True, status="received",
        lead=david, ts=_ago(days=13),
        body_text=(
            "Thanks for the detailed proposal. The partnership terms look solid.\n\n"
            "A few questions:\n"
            "1. What does the follow-up process look like once a referral is made?\n"
            "2. Are there volume-based pricing tiers for enterprise clients?\n\n"
            "David"
        ),
    )
    _make_message(db=db, thread=t2, sender_account=inbox_outreach, direction="outbound",
        mid=m2_3_id, in_reply_to=m2_2_id, references=_refs([m2_1_id, m2_2_id]),
        from_addr="outreach@acmegrowthagency.com", to_addrs=["david.park@growthbridge.co"],
        subject="Re: Partnership Proposal — GrowthBridge", is_read=True, status="sent",
        lead=david, ts=_ago(days=12),
        body_text=(
            "Hi David,\n\nGreat questions!\n\n"
            "1. Follow-up process: Once a referral is submitted, our partnership team does a demo "
            "within 48 hours. You'll receive weekly status updates.\n"
            "2. Enterprise pricing: Yes — for 100+ seat accounts we offer 25% partnership revenue "
            "share plus dedicated support.\n\n"
            "I'll set up a brief follow-up call to finalise the integration timeline. "
            "What works for you this week?\n\nBest,\nOutreach Team"
        ),
    )
    _make_message(db=db, thread=t2, sender_account=inbox_outreach, direction="inbound",
        mid=m2_4_id, in_reply_to=m2_3_id, references=_refs([m2_1_id, m2_2_id, m2_3_id]),
        from_addr="david.park@growthbridge.co", to_addrs=["outreach@acmegrowthagency.com"],
        subject="Re: Partnership Proposal — GrowthBridge", is_read=True, status="received",
        lead=david, ts=_ago(days=10),
        body_text=(
            "The enterprise pricing and follow-up process both work for us.\n\n"
            "Can we also discuss a demo slot for our leadership team?\n\n"
            "David"
        ),
    )
    _make_message(db=db, thread=t2, sender_account=inbox_outreach, direction="outbound",
        mid=m2_5_id, in_reply_to=m2_4_id, references=_refs([m2_1_id, m2_2_id, m2_3_id, m2_4_id]),
        from_addr="outreach@acmegrowthagency.com", to_addrs=["david.park@growthbridge.co"],
        subject="Re: Partnership Proposal — GrowthBridge", is_read=True, status="sent",
        lead=david, ts=_ago(days=5),
        body_text=(
            "Hi David,\n\nAbsolutely! I've scheduled a leadership demo for next Wednesday at 10am.\n\n"
            "I'm also sending over the signed partnership agreement for your review. "
            "We're thrilled to kick off this partnership!\n\nBest,\nOutreach Team"
        ),
    )
    _make_message(db=db, thread=t2, sender_account=inbox_outreach, direction="inbound",
        mid=m2_6_id, in_reply_to=m2_5_id, references=_refs([m2_1_id, m2_2_id, m2_3_id, m2_4_id, m2_5_id]),
        from_addr="david.park@growthbridge.co", to_addrs=["outreach@acmegrowthagency.com"],
        subject="Re: Partnership Proposal — GrowthBridge", is_read=True, status="received",
        lead=david, ts=_ago(days=1),
        body_text=(
            "We're excited to move forward! Agreement signed and returned.\n\n"
            "The pricing model works perfectly for our scale. Let's make this partnership a success!\n\n"
            "David Park\nDirector of Strategy, GrowthBridge"
        ),
    )

    # ───────────────────────────────────────────────────────────────────────────
    # THREAD 3 — Stalled | AI Outreach | john@acme | Marcus Webb
    # ───────────────────────────────────────────────────────────────────────────
    t3 = UniboxThread(
        thread_id=_new_id(),
        workspace_id=ws.workspace_id,
        lead_id=marcus.lead_id,
        campaign_id=camp_ai.campaign_id,
        subject="Scaling DataFlow Systems with AI-Powered Outreach",
        last_message_at=_ago(days=18),
        is_orphan=False,
    )
    db.add(t3); db.flush()

    m3_1_id = _mid("t3-m1")
    m3_2_id = _mid("t3-m2")
    m3_3_id = _mid("t3-m3")

    _make_message(db=db, thread=t3, sender_account=inbox_john, direction="outbound",
        mid=m3_1_id, in_reply_to=None, references=None,
        from_addr="john@acmegrowthagency.com", to_addrs=["marcus.webb@dataflow.io"],
        subject="Scaling DataFlow Systems with AI-Powered Outreach", is_read=True, status="sent",
        lead=marcus, ts=_ago(days=25),
        body_text=(
            "Hi Marcus,\n\nI saw DataFlow's blog post on scaling engineering teams — impressive growth!\n\n"
            "We help VP-level leaders like yourself build smarter outreach pipelines. Our platform "
            "automates follow-up sequences and surfaces high-intent leads so your team focuses on "
            "what matters.\n\nWould a 15-minute demo be worth your time?\n\nJohn\nAcme Growth Agency"
        ),
    )
    _make_message(db=db, thread=t3, sender_account=inbox_john, direction="inbound",
        mid=m3_2_id, in_reply_to=m3_1_id, references=_refs([m3_1_id]),
        from_addr="marcus.webb@dataflow.io", to_addrs=["john@acmegrowthagency.com"],
        subject="Re: Scaling DataFlow Systems with AI-Powered Outreach", is_read=True, status="received",
        lead=marcus, ts=_ago(days=23),
        body_text=(
            "Hi John,\n\nThanks for the note. We're heads-down on our Q1 roadmap right now — "
            "not the best timing. Maybe follow up in Q2?\n\nMarcus"
        ),
    )
    _make_message(db=db, thread=t3, sender_account=inbox_john, direction="outbound",
        mid=m3_3_id, in_reply_to=m3_2_id, references=_refs([m3_1_id, m3_2_id]),
        from_addr="john@acmegrowthagency.com", to_addrs=["marcus.webb@dataflow.io"],
        subject="Re: Scaling DataFlow Systems with AI-Powered Outreach", is_read=True, status="sent",
        lead=marcus, ts=_ago(days=18),
        body_text=(
            "Totally understand, Marcus. Q1 is always full-on.\n\n"
            "I'll follow up in early April. In the meantime, here's a quick case study "
            "on how a similar engineering-led company cut their outreach time by 60%.\n\n"
            "No pressure at all — just wanted to leave something useful.\n\nJohn"
        ),
    )

    # ───────────────────────────────────────────────────────────────────────────
    # THREAD 4 — Stalled | Startup Lead Gen | outreach@acme | Priya Sharma
    # ───────────────────────────────────────────────────────────────────────────
    t4 = UniboxThread(
        thread_id=_new_id(),
        workspace_id=ws.workspace_id,
        lead_id=priya.lead_id,
        campaign_id=camp_startup.campaign_id,
        subject="Intro: CampaignPulse for LaunchPad Ventures",
        last_message_at=_ago(days=9),
        is_orphan=False,
    )
    db.add(t4); db.flush()

    m4_1_id = _mid("t4-m1")
    m4_2_id = _mid("t4-m2")

    _make_message(db=db, thread=t4, sender_account=inbox_outreach, direction="outbound",
        mid=m4_1_id, in_reply_to=None, references=None,
        from_addr="outreach@acmegrowthagency.com", to_addrs=["priya.sharma@launchpad.vc"],
        subject="Intro: CampaignPulse for LaunchPad Ventures", is_read=True, status="sent",
        lead=priya, ts=_ago(days=12),
        body_text=(
            "Hi Priya,\n\nCongratulations on LaunchPad Ventures' recent portfolio expansion!\n\n"
            "I'm reaching out because we work with several VC-backed startups to build "
            "scalable outreach infrastructure. With CampaignPulse, your portfolio companies "
            "can run personalised email campaigns at scale with full analytics and "
            "partnership tracking built in.\n\n"
            "Happy to put together a demo tailored to the startup ecosystem. "
            "Would that be useful?\n\nBest,\nOutreach Team"
        ),
    )
    _make_message(db=db, thread=t4, sender_account=inbox_outreach, direction="inbound",
        mid=m4_2_id, in_reply_to=m4_1_id, references=_refs([m4_1_id]),
        from_addr="priya.sharma@launchpad.vc", to_addrs=["outreach@acmegrowthagency.com"],
        subject="Re: Intro: CampaignPulse for LaunchPad Ventures", is_read=False, status="received",
        lead=priya, ts=_ago(days=9),
        body_text=(
            "Hi,\n\nThanks for reaching out. We're currently in our Q2 budget planning cycle. "
            "Could you follow up end of April? We'll have a clearer picture on budget by then.\n\n"
            "Priya"
        ),
    )

    # ───────────────────────────────────────────────────────────────────────────
    # THREAD 5 — Active | Product Demo | outreach@acme | Emma Thompson
    # ───────────────────────────────────────────────────────────────────────────
    t5 = UniboxThread(
        thread_id=_new_id(),
        workspace_id=ws.workspace_id,
        lead_id=emma.lead_id,
        campaign_id=camp_demo.campaign_id,
        subject="Your Product Demo — Next Steps",
        last_message_at=_ago(hours=18),
        is_orphan=False,
    )
    db.add(t5); db.flush()

    m5_1_id = _mid("t5-m1")
    m5_2_id = _mid("t5-m2")
    m5_3_id = _mid("t5-m3")
    m5_4_id = _mid("t5-m4")

    _make_message(db=db, thread=t5, sender_account=inbox_outreach, direction="outbound",
        mid=m5_1_id, in_reply_to=None, references=None,
        from_addr="outreach@acmegrowthagency.com", to_addrs=["emma.thompson@innovateco.com"],
        subject="Your Product Demo — Next Steps", is_read=True, status="sent",
        lead=emma, ts=_ago(days=10),
        body_text=(
            "Hi Emma,\n\nThank you for attending yesterday's product demo! "
            "It was great to walk through CampaignPulse with you.\n\n"
            "As promised, here's a summary of what we covered:\n"
            "• Unified inbox across all outreach accounts\n"
            "• Automated follow-up sequences with smart scheduling\n"
            "• Full-text search and campaign analytics\n\n"
            "What are your thoughts? Happy to schedule a follow-up or answer any questions.\n\n"
            "Best,\nOutreach Team"
        ),
    )
    _make_message(db=db, thread=t5, sender_account=inbox_outreach, direction="inbound",
        mid=m5_2_id, in_reply_to=m5_1_id, references=_refs([m5_1_id]),
        from_addr="emma.thompson@innovateco.com", to_addrs=["outreach@acmegrowthagency.com"],
        subject="Re: Your Product Demo — Next Steps", is_read=True, status="received",
        lead=emma, ts=_ago(days=9),
        body_text=(
            "Hi,\n\nThe demo was really impressive! Particularly the Unibox and the "
            "full-text search — those would save our team hours every week.\n\n"
            "Quick question: what's the pricing for an enterprise team of 80 people? "
            "We'd want all three inboxes.\n\nEmma"
        ),
    )
    _make_message(db=db, thread=t5, sender_account=inbox_outreach, direction="outbound",
        mid=m5_3_id, in_reply_to=m5_2_id, references=_refs([m5_1_id, m5_2_id]),
        from_addr="outreach@acmegrowthagency.com", to_addrs=["emma.thompson@innovateco.com"],
        subject="Re: Your Product Demo — Next Steps", is_read=True, status="sent",
        lead=emma, ts=_ago(days=7),
        body_text=(
            "Hi Emma,\n\nFor an enterprise team of 80 with three inboxes, "
            "our pricing is $899/month (annual) or $999/month (monthly).\n\n"
            "This includes:\n"
            "• Unlimited campaigns\n"
            "• Full Unibox + search\n"
            "• Priority support + onboarding\n"
            "• Custom partnership integrations\n\n"
            "I can also offer a 14-day free trial so your team can evaluate it hands-on. "
            "Shall I set that up?\n\nBest,\nOutreach Team"
        ),
    )
    _make_message(db=db, thread=t5, sender_account=inbox_outreach, direction="inbound",
        mid=m5_4_id, in_reply_to=m5_3_id, references=_refs([m5_1_id, m5_2_id, m5_3_id]),
        from_addr="emma.thompson@innovateco.com", to_addrs=["outreach@acmegrowthagency.com"],
        subject="Re: Your Product Demo — Next Steps", is_read=False, status="received",
        lead=emma, ts=_ago(hours=18),
        body_text=(
            "Thanks for the pricing details. I'm running this by our internal team this week. "
            "The trial sounds great — I'll come back with a decision by Friday.\n\n"
            "Could you also share more details on the partnership integration options?\n\nEmma"
        ),
    )

    # ───────────────────────────────────────────────────────────────────────────
    # THREAD 6 — Cold no-reply | Startup Lead Gen | outreach@acme | Alex Rodriguez
    # ───────────────────────────────────────────────────────────────────────────
    t6 = UniboxThread(
        thread_id=_new_id(),
        workspace_id=ws.workspace_id,
        lead_id=alex.lead_id,
        campaign_id=camp_startup.campaign_id,
        subject="Startup Growth Engine — ScaleUp Inc",
        last_message_at=_ago(days=5),
        is_orphan=False,
    )
    db.add(t6); db.flush()

    _make_message(db=db, thread=t6, sender_account=inbox_outreach, direction="outbound",
        mid=_mid("t6-m1"), in_reply_to=None, references=None,
        from_addr="outreach@acmegrowthagency.com", to_addrs=["alex.rodriguez@scaleup.io"],
        subject="Startup Growth Engine — ScaleUp Inc", is_read=True, status="sent",
        lead=alex, ts=_ago(days=5),
        body_text=(
            "Hi Alex,\n\nScaleUp's growth trajectory caught my attention — 3x ARR in 12 months "
            "is impressive!\n\nWe help Head of Growth leaders at high-velocity startups build "
            "outreach systems that scale. Our demo takes 20 minutes and typically generates "
            "a 40% lift in replied rate within the first 30 days.\n\n"
            "Worth a follow-up call this week?\n\nBest,\nOutreach Team\nAcme Growth Agency"
        ),
    )

    # ───────────────────────────────────────────────────────────────────────────
    # THREAD 7 — Active | AI Outreach | john@acme | Jordan Kim
    # ───────────────────────────────────────────────────────────────────────────
    t7 = UniboxThread(
        thread_id=_new_id(),
        workspace_id=ws.workspace_id,
        lead_id=jordan.lead_id,
        campaign_id=camp_ai.campaign_id,
        subject="AI Strategy Partnership — NexGenAI",
        last_message_at=_ago(hours=6),
        is_orphan=False,
    )
    db.add(t7); db.flush()

    m7_1_id = _mid("t7-m1")
    m7_2_id = _mid("t7-m2")
    m7_3_id = _mid("t7-m3")
    m7_4_id = _mid("t7-m4")

    _make_message(db=db, thread=t7, sender_account=inbox_john, direction="outbound",
        mid=m7_1_id, in_reply_to=None, references=None,
        from_addr="john@acmegrowthagency.com", to_addrs=["jordan.kim@nexgenai.co"],
        subject="AI Strategy Partnership — NexGenAI", is_read=True, status="sent",
        lead=jordan, ts=_ago(days=8),
        body_text=(
            "Hi Jordan,\n\nNexGenAI's vision of agent-first workflows is exactly where we see "
            "the market heading.\n\nWe're building strategic AI partnerships with founders who "
            "are defining the next generation of tooling. I think there's a strong "
            "mutual fit here — would love to explore a partnership.\n\n"
            "Are you open to a quick call to discuss?\n\nJohn\nAcme Growth Agency"
        ),
    )
    _make_message(db=db, thread=t7, sender_account=inbox_john, direction="inbound",
        mid=m7_2_id, in_reply_to=m7_1_id, references=_refs([m7_1_id]),
        from_addr="jordan.kim@nexgenai.co", to_addrs=["john@acmegrowthagency.com"],
        subject="Re: AI Strategy Partnership — NexGenAI", is_read=True, status="received",
        lead=jordan, ts=_ago(days=6),
        body_text=(
            "Hey John,\n\nInteresting — I'd be curious to learn more. "
            "Can you share your partnership terms and a demo link? "
            "What does pricing look like for early-stage teams?\n\nJordan"
        ),
    )
    _make_message(db=db, thread=t7, sender_account=inbox_john, direction="outbound",
        mid=m7_3_id, in_reply_to=m7_2_id, references=_refs([m7_1_id, m7_2_id]),
        from_addr="john@acmegrowthagency.com", to_addrs=["jordan.kim@nexgenai.co"],
        subject="Re: AI Strategy Partnership — NexGenAI", is_read=False, status="sent",
        lead=jordan, ts=_ago(hours=12),
        body_text=(
            "Jordan,\n\nLove the directness! Here's the breakdown:\n\n"
            "Partnership model:\n"
            "• Co-development of AI outreach integrations\n"
            "• 25% revenue share on mutual referrals\n"
            "• Early access to our partner API\n\n"
            "Pricing for early-stage: $149/month with a 6-month lock-in.\n\n"
            "Demo link: https://app.campaignpulse.io/demo/nexgenai\n\n"
            "Let me know if you'd like to get on a follow-up call this week!\n\nJohn"
        ),
    )
    _make_message(db=db, thread=t7, sender_account=inbox_john, direction="inbound",
        mid=m7_4_id, in_reply_to=m7_3_id, references=_refs([m7_1_id, m7_2_id, m7_3_id]),
        from_addr="jordan.kim@nexgenai.co", to_addrs=["john@acmegrowthagency.com"],
        subject="Re: AI Strategy Partnership — NexGenAI", is_read=False, status="received",
        lead=jordan, ts=_ago(hours=6),
        body_text=(
            "This looks interesting. I'm watching the demo now.\n\n"
            "Can we schedule a follow-up call Thursday morning? "
            "I'll have my CTO join.\n\nJordan"
        ),
    )

    # ───────────────────────────────────────────────────────────────────────────
    # THREAD 8 — Support thread | support@acme | Lily Wang | ConnectHub
    # ───────────────────────────────────────────────────────────────────────────
    t8 = UniboxThread(
        thread_id=_new_id(),
        workspace_id=ws.workspace_id,
        lead_id=lily.lead_id,
        campaign_id=camp_demo.campaign_id,
        subject="Support Request — CampaignPulse Integration",
        last_message_at=_ago(hours=30),
        is_orphan=False,
    )
    db.add(t8); db.flush()

    m8_1_id = _mid("t8-m1")
    m8_2_id = _mid("t8-m2")
    m8_3_id = _mid("t8-m3")

    _make_message(db=db, thread=t8, sender_account=inbox_support, direction="inbound",
        mid=m8_1_id, in_reply_to=None, references=None,
        from_addr="lily.wang@connecthub.io", to_addrs=["support@acmegrowthagency.com"],
        subject="Support Request — CampaignPulse Integration", is_read=True, status="received",
        lead=lily, ts=_ago(days=3),
        body_text=(
            "Hi Support Team,\n\nWe're evaluating CampaignPulse for ConnectHub and ran into "
            "a question about the integration API.\n\n"
            "Specifically: does your platform support webhook-based follow-up triggers? "
            "We'd also love to understand the partnership pricing for a team of 25.\n\n"
            "Thanks,\nLily Wang\nHead of Partnerships, ConnectHub"
        ),
    )
    _make_message(db=db, thread=t8, sender_account=inbox_support, direction="outbound",
        mid=m8_2_id, in_reply_to=m8_1_id, references=_refs([m8_1_id]),
        from_addr="support@acmegrowthagency.com", to_addrs=["lily.wang@connecthub.io"],
        subject="Re: Support Request — CampaignPulse Integration", is_read=True, status="sent",
        lead=lily, ts=_ago(days=2),
        body_text=(
            "Hi Lily,\n\nThanks for reaching out!\n\n"
            "Yes, we fully support webhook-based follow-up triggers. Here's how it works:\n"
            "• Configure a webhook endpoint in your account settings\n"
            "• Events: email_opened, replied, link_clicked, demo_scheduled\n"
            "• Full documentation: https://docs.campaignpulse.io/webhooks\n\n"
            "For a team of 25, our partnership pricing starts at $399/month with access to "
            "all three inbox accounts included.\n\n"
            "Happy to schedule a demo if that would help!\n\nSupport Team\nAcme Growth Agency"
        ),
    )
    _make_message(db=db, thread=t8, sender_account=inbox_support, direction="inbound",
        mid=m8_3_id, in_reply_to=m8_2_id, references=_refs([m8_1_id, m8_2_id]),
        from_addr="lily.wang@connecthub.io", to_addrs=["support@acmegrowthagency.com"],
        subject="Re: Support Request — CampaignPulse Integration", is_read=False, status="received",
        lead=lily, ts=_ago(hours=30),
        body_text=(
            "Perfect, the webhook docs are exactly what we needed.\n\n"
            "One more question — does the partnership program include co-marketing? "
            "We'd love to do a joint follow-up campaign in Q2.\n\n"
            "Lily"
        ),
    )

    # ===========================================================================
    # ORPHAN THREADS
    # ===========================================================================

    # ── Orphan 1: vendor@cloudtech.io — Pricing Inquiry ───────────────────────
    ot1 = UniboxThread(
        thread_id=_new_id(),
        workspace_id=ws.workspace_id,
        lead_id=None,
        campaign_id=None,
        subject="Pricing Inquiry — Cloud Storage Partnership",
        last_message_at=_ago(days=2),
        is_orphan=True,
    )
    db.add(ot1); db.flush()

    o1_1_id = _mid("ot1-m1")
    o1_2_id = _mid("ot1-m2")

    _make_message(db=db, thread=ot1, sender_account=inbox_outreach, direction="inbound",
        mid=o1_1_id, in_reply_to=None, references=None,
        from_addr="vendor@cloudtech.io", to_addrs=["outreach@acmegrowthagency.com"],
        subject="Pricing Inquiry — Cloud Storage Partnership", is_read=False, status="received",
        ts=_ago(days=3),
        body_text=(
            "Hi,\n\nI'm reaching out from CloudTech. We're an infrastructure company and came "
            "across CampaignPulse in a review article.\n\n"
            "We're interested in understanding your pricing for a potential partnership — "
            "specifically around the demo and follow-up automation modules.\n\n"
            "Could you send over a pricing sheet?\n\nThanks,\nVendor Team\nCloudTech"
        ),
    )
    _make_message(db=db, thread=ot1, sender_account=inbox_outreach, direction="inbound",
        mid=o1_2_id, in_reply_to=o1_1_id, references=_refs([o1_1_id]),
        from_addr="vendor@cloudtech.io", to_addrs=["outreach@acmegrowthagency.com"],
        subject="Re: Pricing Inquiry — Cloud Storage Partnership", is_read=False, status="received",
        ts=_ago(days=2),
        body_text=(
            "Following up on my previous email about partnership pricing. "
            "We're keen to move forward and would love to schedule a demo.\n\n"
            "Best,\nVendor Team"
        ),
    )

    # ── Orphan 2: recruiter@headhunters.com — Partnership Opportunity ──────────
    ot2 = UniboxThread(
        thread_id=_new_id(),
        workspace_id=ws.workspace_id,
        lead_id=None,
        campaign_id=None,
        subject="Exciting Partnership Opportunity",
        last_message_at=_ago(days=4),
        is_orphan=True,
    )
    db.add(ot2); db.flush()

    _make_message(db=db, thread=ot2, sender_account=inbox_john, direction="inbound",
        mid=_mid("ot2-m1"), in_reply_to=None, references=None,
        from_addr="recruiter@headhunters.com", to_addrs=["john@acmegrowthagency.com"],
        subject="Exciting Partnership Opportunity", is_read=True, status="received",
        ts=_ago(days=4),
        body_text=(
            "Hi there,\n\nOur firm specialises in placing senior executives in high-growth SaaS "
            "companies. We've placed 3 CROs in the outreach space this quarter.\n\n"
            "I think there's a strong partnership angle here — we refer growth-stage companies "
            "your way, you refer scaling teams to us for executive placement.\n\n"
            "Worth a 20-minute follow-up call?\n\nBest,\nHeadHunters Recruiting"
        ),
    )

    # ── Orphan 3: admin@techdigest.com — Demo Request ─────────────────────────
    ot3 = UniboxThread(
        thread_id=_new_id(),
        workspace_id=ws.workspace_id,
        lead_id=None,
        campaign_id=None,
        subject="Demo Request — TechDigest Media",
        last_message_at=_ago(hours=48),
        is_orphan=True,
    )
    db.add(ot3); db.flush()

    _make_message(db=db, thread=ot3, sender_account=inbox_support, direction="inbound",
        mid=_mid("ot3-m1"), in_reply_to=None, references=None,
        from_addr="admin@techdigest.com", to_addrs=["support@acmegrowthagency.com"],
        subject="Demo Request — TechDigest Media", is_read=False, status="received",
        ts=_ago(hours=48),
        body_text=(
            "Hello,\n\nI'm the Managing Editor at TechDigest — we cover SaaS tools for "
            "growth teams. I'd love to schedule a demo of CampaignPulse for a review piece "
            "we're writing on email outreach platforms.\n\n"
            "What does pricing look like for a media/editorial team of 5? "
            "Is there a partner or press pricing option?\n\n"
            "Thanks,\nAdmin\nTechDigest Media"
        ),
    )

    # ===========================================================================
    # Commit everything
    # ===========================================================================
    db.commit()
    print("[OK] Demo data seeded successfully!\n")
    _print_summary(ws.workspace_id)


def _print_summary(workspace_id: str) -> None:
    print("━" * 60)
    print("  UNIBOX DEMO LOGIN")
    print("━" * 60)
    print(f"  Email:     {DEMO_USER_EMAIL}")
    print(f"  Password:  {DEMO_USER_PASSWORD}")
    print(f"  Workspace: [DEMO] Acme Growth Agency")
    print("━" * 60)
    print()
    print("  SEEDED DATA SUMMARY")
    print("  ─────────────────────────────────────────")
    print("  Inboxes:    john@, outreach@, support@")
    print("  Campaigns:  AI Outreach Q1 | Startup Lead Gen | Product Demo")
    print("  Leads:      8 (Sarah, Marcus, Jordan, Priya, Alex, Emma, David, Lily)")
    print("  Threads:    8 conversations + 3 orphan threads = 11 total")
    print()
    print("  THREAD OVERVIEW")
    print("  ─────────────────────────────────────────")
    print("  [ACTIVE]   Sarah Chen    → AI Integration (5 msgs, meeting-booked)")
    print("  [WON]      David Park    → Partnership (6 msgs, won)")
    print("  [STALLED]  Marcus Webb   → DataFlow (3 msgs, lead)")
    print("  [STALLED]  Priya Sharma  → LaunchPad (2 msgs, interested)")
    print("  [ACTIVE]   Emma Thompson → Product Demo (4 msgs, meeting-completed)")
    print("  [COLD]     Alex Rodriguez→ ScaleUp (1 msg, no reply)")
    print("  [ACTIVE]   Jordan Kim    → NexGenAI (4 msgs, interested)")
    print("  [SUPPORT]  Lily Wang     → ConnectHub (3 msgs, interested)")
    print("  [ORPHAN]   vendor@cloudtech.io (2 msgs, unknown sender)")
    print("  [ORPHAN]   recruiter@headhunters.com (1 msg, unknown sender)")
    print("  [ORPHAN]   admin@techdigest.com (1 msg, unknown sender)")
    print()
    print("  SEARCH KEYWORDS TO TEST")
    print("  ─────────────────────────────────────────")
    print("  pricing | demo | partnership | follow-up")
    print("━" * 60)


# ===========================================================================
# Entry point
# ===========================================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Unibox demo data seed script")
    parser.add_argument("--cleanup", action="store_true", help="Remove all demo data")
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.cleanup:
            cleanup(db)
        else:
            seed(db)
