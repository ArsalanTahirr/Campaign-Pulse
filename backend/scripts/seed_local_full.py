#!/usr/bin/env python3
"""
scripts/seed_local_full.py — One-shot local database seed for Campaign Pulse.

Creates in a single workspace:
  • Multiple fake users with LocalAuth (password login)
  • Workspace + collaborators (Owner, Marketing Manager, Data Analyst)
  • Sender (email) accounts
  • Campaigns + sequence steps + leads
  • EmailEvent rows (sent / opened / clicked / replied) for the Analytics dashboard
  • Unibox threads + messages (linked leads + one orphan thread)

Usage (from repo root or backend/):
  python backend/scripts/seed_local_full.py
  python backend/scripts/seed_local_full.py --cleanup

Idempotency: skips if workspace "[LOCAL] Full Demo" already exists (use --cleanup to re-run).

SAFETY: Refuses when DATABASE_URL contains "prod" unless ALLOW_SEED_IN_PROD=true.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(dotenv_path=_BACKEND_DIR.parent / ".env")

_DB_URL = os.environ.get("DATABASE_URL", "")
if not _DB_URL:
    print("ERROR: DATABASE_URL is not set in .env")
    sys.exit(1)
if "prod" in _DB_URL.lower() and os.environ.get("ALLOW_SEED_IN_PROD") != "true":
    print("ERROR: DATABASE_URL looks like production. Set ALLOW_SEED_IN_PROD=true to override.")
    sys.exit(1)

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

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
    StepEmail,
    UniboxMessage,
    UniboxThread,
    User,
    Workspace,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORKSPACE_NAME = "[LOCAL] Full Demo"
DOMAIN = "local-full.demo"

SEED_USERS: list[dict[str, str]] = [
    {
        "email": f"owner@{DOMAIN}",
        "password": "OwnerPass123!",
        "first_name": "Olivia",
        "last_name": "Owner",
        "role_name": "Owner",
    },
    {
        "email": f"marketer@{DOMAIN}",
        "password": "MarketPass123!",
        "first_name": "Morgan",
        "last_name": "Marketer",
        "role_name": "Marketing Manager",
    },
    {
        "email": f"analyst@{DOMAIN}",
        "password": "AnalystPass123!",
        "first_name": "Alex",
        "last_name": "Analyst",
        "role_name": "Data Analyst",
    },
]

LEADS_PER_CAMPAIGN = 8
NOW = datetime.now(timezone.utc)

engine = create_engine(_DB_URL, poolclass=NullPool)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

_TRIGGERS = [
    ("campaign", "trg_campaign_soft_delete"),
    ("lead", "trg_guard_lead_mutation_on_completed"),
    ("sequence_step", "trg_guard_sequence_step_mutation"),
]


def _uid() -> str:
    return str(uuid.uuid4())


def _ago(**kwargs: Any) -> datetime:
    return NOW - timedelta(**kwargs)


def _role(db: Session, name: str) -> Role:
    r = db.query(Role).filter(Role.role_name == name).first()
    if not r:
        r = Role(role_id=_uid(), role_name=name, permissions={})
        db.add(r)
        db.flush()
    return r


def _get_or_create_user(
    db: Session,
    *,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
) -> User:
    u = db.query(User).filter(User.email == email).first()
    if u:
        return u
    u = User(
        user_id=_uid(),
        email=email,
        first_name=first_name,
        last_name=last_name,
        is_verified=True,
    )
    db.add(u)
    db.flush()
    db.add(
        LocalAuth(
            user_id=u.user_id,
            password_hash=hash_password(password),
            verification_token=None,
        )
    )
    db.flush()
    return u


def _tsv(db: Session, content: str):
    return db.execute(text("SELECT to_tsvector('english', :c)"), {"c": content}).scalar()


def _make_unibox_message(
    db: Session,
    *,
    thread: UniboxThread,
    sender_account: SenderAccount,
    lead: Optional[Lead],
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
    ts: datetime,
) -> None:
    msg = UniboxMessage(
        message_id=_uid(),
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
        is_orphan=lead is None,
        status=status,
        received_at=ts if direction == "inbound" else None,
        sent_at=ts if direction == "outbound" else None,
        search_vector=_tsv(db, f"{subject} {body_text} {from_addr}"),
    )
    db.add(msg)


def _event(
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
# Cleanup
# ---------------------------------------------------------------------------


def cleanup() -> None:
    db = SessionLocal()
    try:
        row = db.execute(
            text("SELECT workspace_id::text FROM workspace WHERE workspace_name = :n"),
            {"n": WORKSPACE_NAME},
        ).fetchone()
        if not row:
            print("No full-demo workspace found. Nothing to remove.")
            return
        ws_id = row[0]
        emails = [u["email"] for u in SEED_USERS]

        for table, trigger in _TRIGGERS:
            db.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER {trigger}"))

        db.execute(
            text(
                "DELETE FROM unibox_message WHERE thread_id IN "
                "(SELECT thread_id FROM unibox_thread WHERE workspace_id = :ws)"
            ),
            {"ws": ws_id},
        )
        db.execute(text("DELETE FROM unibox_thread WHERE workspace_id = :ws"), {"ws": ws_id})

        cid_rows = db.execute(
            text("SELECT campaign_id::text FROM campaign WHERE workspace_id = :ws"),
            {"ws": ws_id},
        ).fetchall()
        cids = [r[0] for r in cid_rows]
        if cids:
            inl = ", ".join(f"'{c}'" for c in cids)
            db.execute(text(f"DELETE FROM campaign_run WHERE campaign_id IN ({inl})"))
            db.execute(
                text(
                    f"DELETE FROM email_event WHERE lead_id IN "
                    f"(SELECT lead_id FROM lead WHERE campaign_id IN ({inl}))"
                )
            )
            db.execute(text(f"DELETE FROM step_email WHERE step_id IN (SELECT step_id FROM sequence_step WHERE campaign_id IN ({inl}))"))
            db.execute(text(f"DELETE FROM sequence_step WHERE campaign_id IN ({inl})"))
            db.execute(text(f"DELETE FROM campaign_sender_pool WHERE campaign_id IN ({inl})"))
            db.execute(text(f"DELETE FROM lead WHERE campaign_id IN ({inl})"))
            db.execute(text(f"DELETE FROM campaign WHERE campaign_id IN ({inl})"))

        db.execute(text("DELETE FROM invitation WHERE workspace_id = :ws"), {"ws": ws_id})
        db.execute(text("DELETE FROM audit_log WHERE workspace_id = :ws"), {"ws": ws_id})
        db.execute(
            text(
                "DELETE FROM warmup_settings WHERE account_id IN "
                "(SELECT account_id FROM sender_account WHERE workspace_id = :ws)"
            ),
            {"ws": ws_id},
        )
        db.execute(text("DELETE FROM sender_account WHERE workspace_id = :ws"), {"ws": ws_id})
        db.execute(text("DELETE FROM collaborator WHERE workspace_id = :ws"), {"ws": ws_id})
        db.execute(text("DELETE FROM workspace WHERE workspace_id = :ws"), {"ws": ws_id})

        for em in emails:
            db.execute(text("DELETE FROM local_auth WHERE user_id IN (SELECT user_id FROM users WHERE email = :e)"), {"e": em})
            db.execute(text("DELETE FROM users WHERE email = :e"), {"e": em})

        for table, trigger in _TRIGGERS:
            db.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER {trigger}"))

        db.commit()
        print(f"Removed workspace '{WORKSPACE_NAME}' and seed users ({', '.join(emails)}).")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------


def seed() -> None:
    db = SessionLocal()
    try:
        if db.query(Workspace).filter(Workspace.workspace_name == WORKSPACE_NAME).first():
            print(f"Already seeded (workspace '{WORKSPACE_NAME}' exists). Use --cleanup first.")
            return

        print(f"Seeding {WORKSPACE_NAME}…")

        users: list[User] = []
        for spec in SEED_USERS:
            users.append(
                _get_or_create_user(
                    db,
                    email=spec["email"],
                    password=spec["password"],
                    first_name=spec["first_name"],
                    last_name=spec["last_name"],
                )
            )
        owner_user = users[0]
        db.flush()

        ws = Workspace(workspace_id=_uid(), workspace_name=WORKSPACE_NAME)
        db.add(ws)
        db.flush()

        owner_collab = Collaborator(
            member_id=_uid(),
            workspace_id=ws.workspace_id,
            user_id=owner_user.user_id,
            role_id=_role(db, "Owner").role_id,
            invite_status="accepted",
            joined_at=NOW,
        )
        db.add(owner_collab)
        db.add(
            Collaborator(
                member_id=_uid(),
                workspace_id=ws.workspace_id,
                user_id=users[1].user_id,
                role_id=_role(db, "Marketing Manager").role_id,
                invite_status="accepted",
                joined_at=NOW,
            )
        )
        db.add(
            Collaborator(
                member_id=_uid(),
                workspace_id=ws.workspace_id,
                user_id=users[2].user_id,
                role_id=_role(db, "Data Analyst").role_id,
                invite_status="accepted",
                joined_at=NOW,
            )
        )
        db.flush()

        senders = [
            SenderAccount(
                account_id=_uid(),
                workspace_id=ws.workspace_id,
                provider_type="smtp",
                email=f"outreach-a@{DOMAIN}",
                status="active",
                is_verified=True,
                daily_sending_limit=200,
            ),
            SenderAccount(
                account_id=_uid(),
                workspace_id=ws.workspace_id,
                provider_type="smtp",
                email=f"outreach-b@{DOMAIN}",
                status="active",
                is_verified=True,
                daily_sending_limit=200,
            ),
        ]
        db.add_all(senders)
        db.flush()
        inbox_a, inbox_b = senders[0], senders[1]

        campaigns_cfg = [
            ("Spring Outreach", "active"),
            ("Product Launch", "active"),
            ("Winter Nurture", "completed"),
        ]
        campaigns: list[Campaign] = []
        steps: list[SequenceStep] = []

        for name, target_status in campaigns_cfg:
            c = Campaign(
                campaign_id=_uid(),
                workspace_id=ws.workspace_id,
                created_by=owner_collab.member_id,
                campaign_name=name,
                status="draft",
                open_tracking_enabled=True,
            )
            db.add(c)
            db.flush()
            campaigns.append(c)

            for s in senders:
                db.add(CampaignSenderPool(campaign_id=c.campaign_id, sender_account_id=s.account_id))
            st = SequenceStep(
                step_id=_uid(),
                campaign_id=c.campaign_id,
                step_number=1,
                wait_days=0,
                send_time="09:00",
                send_window_end="17:00",
                send_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            )
            db.add(st)
            db.flush()
            steps.append(st)
            db.add(
                StepEmail(
                    email_id=_uid(),
                    step_id=st.step_id,
                    subject_line="Hi {{first_name}} — quick idea for {{company_name}}",
                    email_body="<p>Hello {{first_name}},</p><p>Worth a short chat?</p>",
                )
            )
            db.flush()

        # Leads + analytics events (while campaigns still draft)
        all_leads: list[Lead] = []
        for camp_idx, camp in enumerate(campaigns):
            for i in range(LEADS_PER_CAMPAIGN):
                st = steps[camp_idx]
                sender = senders[i % 2]
                days_ago = (i % 14) + 1
                sent_at = NOW - timedelta(days=days_ago, hours=10)
                pipe_cycle = ["lead", "interested", "meeting-booked", "meeting-completed", "won"]
                pipeline = pipe_cycle[i % len(pipe_cycle)]

                lead = Lead(
                    lead_id=_uid(),
                    campaign_id=camp.campaign_id,
                    email=f"prospect-{camp_idx}-{i:02d}@{DOMAIN}",
                    first_name="Pat",
                    last_name=f"Prospect{camp_idx}{i}",
                    company_name=f"Co {camp_idx}-{i}",
                    lead_status="replied" if i % 4 == 0 else "active",
                    pipeline_status=pipeline,
                    delivery_state="paused",
                    is_opportunity=(i % 5 == 0),
                )
                db.add(lead)
                db.flush()
                all_leads.append(lead)

                db.add(_event(lead.lead_id, st.step_id, "sent", sender.account_id, sent_at))
                if i % 2 == 0:
                    db.add(_event(lead.lead_id, st.step_id, "opened", sender.account_id, sent_at + timedelta(hours=1)))
                if i % 3 == 0:
                    db.add(
                        _event(
                            lead.lead_id,
                            st.step_id,
                            "clicked",
                            sender.account_id,
                            sent_at + timedelta(hours=2),
                        )
                    )
                if i % 4 == 0:
                    db.add(_event(lead.lead_id, st.step_id, "replied", sender.account_id, sent_at + timedelta(hours=5)))

        db.flush()

        for c, (_, target_status) in zip(campaigns, campaigns_cfg):
            c.status = target_status
        db.flush()

        # --- Unibox sample threads (first two leads of first campaign) ---
        L0 = all_leads[0]
        L1 = all_leads[1]
        c0 = campaigns[0]

        t1 = UniboxThread(
            thread_id=_uid(),
            workspace_id=ws.workspace_id,
            lead_id=L0.lead_id,
            campaign_id=c0.campaign_id,
            subject="Re: Spring pilot — TechCorp",
            last_message_at=_ago(hours=2),
            is_orphan=False,
        )
        t2 = UniboxThread(
            thread_id=_uid(),
            workspace_id=ws.workspace_id,
            lead_id=L1.lead_id,
            campaign_id=c0.campaign_id,
            subject="Pricing question",
            last_message_at=_ago(days=1),
            is_orphan=False,
        )
        db.add_all([t1, t2])
        db.flush()

        m1 = f"<full-demo-t1-m1@{DOMAIN}>"
        m2 = f"<full-demo-t1-m2@{DOMAIN}>"
        _make_unibox_message(
            db,
            thread=t1,
            sender_account=inbox_a,
            lead=L0,
            direction="outbound",
            mid=m1,
            in_reply_to=None,
            references=None,
            from_addr=inbox_a.email,
            to_addrs=[L0.email],
            subject=t1.subject,
            body_text="Hi Pat — following up on our Spring pilot. Can we book 15 minutes?",
            is_read=True,
            status="sent",
            ts=_ago(days=2),
        )
        _make_unibox_message(
            db,
            thread=t1,
            sender_account=inbox_a,
            lead=L0,
            direction="inbound",
            mid=m2,
            in_reply_to=m1,
            references=m1,
            from_addr=L0.email,
            to_addrs=[inbox_a.email],
            subject=f"Re: {t1.subject}",
            body_text="Yes — Thursday 3pm works for us.",
            is_read=False,
            status="received",
            ts=_ago(hours=2),
        )

        m3 = f"<full-demo-t2-m1@{DOMAIN}>"
        _make_unibox_message(
            db,
            thread=t2,
            sender_account=inbox_b,
            lead=L1,
            direction="inbound",
            mid=m3,
            in_reply_to=None,
            references=None,
            from_addr=L1.email,
            to_addrs=[inbox_b.email],
            subject=t2.subject,
            body_text="Could you share annual pricing for 50 seats?",
            is_read=True,
            status="received",
            ts=_ago(days=1),
        )

        # Orphan thread
        ot = UniboxThread(
            thread_id=_uid(),
            workspace_id=ws.workspace_id,
            lead_id=None,
            campaign_id=None,
            subject="Unknown sender — partnership",
            last_message_at=_ago(hours=12),
            is_orphan=True,
        )
        db.add(ot)
        db.flush()
        _make_unibox_message(
            db,
            thread=ot,
            sender_account=inbox_a,
            lead=None,
            direction="inbound",
            mid=f"<orphan-unknown@{DOMAIN}>",
            in_reply_to=None,
            references=None,
            from_addr=f"stranger@{DOMAIN}",
            to_addrs=[inbox_a.email],
            subject=ot.subject,
            body_text="We'd like to discuss a reseller partnership.",
            is_read=False,
            status="received",
            ts=_ago(hours=12),
        )

        db.commit()

        print("\nDone.\n")
        print("=" * 58)
        print("  WORKSPACE:", WORKSPACE_NAME)
        print("  LOG IN AS (any collaborator):")
        for spec in SEED_USERS:
            print(f"    • {spec['email']} / {spec['password']} ({spec['role_name']})")
        print("=" * 58)
        print(f"  Campaigns:     {len(campaigns)}")
        print(f"  Leads:         {len(all_leads)}")
        print(f"  Sender accts:  {len(senders)}")
        print(f"  Unibox:        2 linked threads + 1 orphan")
        print("  Analytics:     email_event rows (sent/open/click/reply) populated")
        print("=" * 58)
        print("\nUse --cleanup to remove this demo data.\n")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed local DB with full demo data")
    parser.add_argument("--cleanup", action="store_true", help="Remove seeded workspace and users")
    args = parser.parse_args()
    if args.cleanup:
        cleanup()
    else:
        seed()


if __name__ == "__main__":
    main()
