#!/usr/bin/env python3
"""
reset_unibox_imap_test.py — Clear Unibox data and IMAP scan cursors for iterative testing.

What it does (for one workspace):
  • Deletes all UniboxMessage rows in that workspace, then all UniboxThread rows.
  • Sets sender_account.last_imap_uid to NULL so the next IMAP scan starts from
    the beginning of the mailbox UID range (same as a fresh connection).
  • Unless --no-lead-mutation: deletes EmailEvent rows with event_type='replied'
    for leads that belong to campaigns in that workspace, and resets those leads
    to lead_status='active' and delivery_state='queued' so reply detection can be
    exercised again.

Usage (from repo root or backend/):
  python backend/scripts/reset_unibox_imap_test.py --list-workspaces
  python backend/scripts/reset_unibox_imap_test.py --workspace-id <uuid>
  python backend/scripts/reset_unibox_imap_test.py --workspace-name "My Team"

Options:
  --unibox-only          Only delete threads/messages; do not touch last_imap_uid.
  --imap-only            Only clear last_imap_uid for senders in the workspace.
  --no-lead-mutation     Do not delete reply EmailEvents or reset lead rows.

SAFETY: Refuses if DATABASE_URL contains "prod" unless ALLOW_SEED_IN_PROD=true.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

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

from sqlalchemy import create_engine, func  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.models import (  # noqa: E402
    Campaign,
    EmailEvent,
    Lead,
    SenderAccount,
    UniboxMessage,
    UniboxThread,
    Workspace,
)


def _engine():
    return create_engine(_DB_URL, poolclass=NullPool)


def list_workspaces(db: Session) -> None:
    rows = db.query(Workspace.workspace_id, Workspace.workspace_name).order_by(Workspace.workspace_name).all()
    if not rows:
        print("No workspaces found.")
        return
    print("workspace_id\tworkspace_name")
    for wid, name in rows:
        print(f"{wid}\t{name}")


def resolve_workspace_id(db: Session, args: argparse.Namespace) -> str:
    if args.workspace_id:
        ws = db.query(Workspace).filter(Workspace.workspace_id == args.workspace_id.strip()).first()
        if not ws:
            print(f"ERROR: No workspace with id {args.workspace_id!r}")
            sys.exit(1)
        return ws.workspace_id
    if args.workspace_name:
        name = args.workspace_name.strip()
        ws = (
            db.query(Workspace)
            .filter(func.lower(Workspace.workspace_name) == func.lower(name))
            .first()
        )
        if not ws:
            print(f"ERROR: No workspace with name matching {name!r} (case-insensitive)")
            sys.exit(1)
        return ws.workspace_id
    print("ERROR: Pass --workspace-id or --workspace-name (or use --list-workspaces).")
    sys.exit(1)


def run_reset(db: Session, workspace_id: str, args: argparse.Namespace) -> None:
    full = not args.unibox_only and not args.imap_only

    n_msg = 0
    n_thread = 0
    n_imap = 0
    n_events = 0
    n_leads = 0

    thread_ids_subq = (
        db.query(UniboxThread.thread_id).filter(UniboxThread.workspace_id == workspace_id).scalar_subquery()
    )

    if full or args.unibox_only:
        n_msg = (
            db.query(UniboxMessage)
            .filter(UniboxMessage.thread_id.in_(db.query(UniboxThread.thread_id).filter(UniboxThread.workspace_id == workspace_id)))
            .delete(synchronize_session=False)
        )
        n_thread = (
            db.query(UniboxThread).filter(UniboxThread.workspace_id == workspace_id).delete(synchronize_session=False)
        )

    n_senders = 0
    if full or args.imap_only:
        accounts = db.query(SenderAccount).filter(SenderAccount.workspace_id == workspace_id).all()
        n_senders = len(accounts)
        for acc in accounts:
            if acc.last_imap_uid is not None:
                acc.last_imap_uid = None
                n_imap += 1

    if full and not args.no_lead_mutation:
        lead_ids_subq = (
            db.query(Lead.lead_id).join(Campaign, Campaign.campaign_id == Lead.campaign_id).filter(
                Campaign.workspace_id == workspace_id
            )
        )
        n_events = (
            db.query(EmailEvent)
            .filter(EmailEvent.lead_id.in_(lead_ids_subq), EmailEvent.event_type == "replied")
            .delete(synchronize_session=False)
        )
        leads = (
            db.query(Lead)
            .join(Campaign, Campaign.campaign_id == Lead.campaign_id)
            .filter(Campaign.workspace_id == workspace_id, Lead.lead_status == "replied")
            .all()
        )
        for lead in leads:
            lead.lead_status = "active"
            lead.delivery_state = "queued"
            n_leads += 1

    db.commit()

    print("Done.")
    if full or args.unibox_only:
        print(f"  Deleted UniboxMessage: {n_msg}")
        print(f"  Deleted UniboxThread:  {n_thread}")
    if full or args.imap_only:
        print(
            f"  Sender accounts in workspace: {n_senders} "
            f"(cleared non-null last_imap_uid on {n_imap} of them)."
        )
    if full and not args.no_lead_mutation:
        print(f"  Deleted replied EmailEvent rows: {n_events}")
        print(f"  Reset replied leads to active/queued: {n_leads}")
    if args.no_lead_mutation and full:
        print("  (--no-lead-mutation) Left EmailEvent + lead status unchanged.")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--list-workspaces", action="store_true", help="Print workspace ids and names, then exit.")
    p.add_argument("--workspace-id", type=str, default=None, help="Target workspace UUID.")
    p.add_argument("--workspace-name", type=str, default=None, help="Target workspace name (case-insensitive).")
    p.add_argument("--unibox-only", action="store_true", help="Only remove Unibox threads/messages.")
    p.add_argument("--imap-only", action="store_true", help="Only clear IMAP UID cursors for workspace senders.")
    p.add_argument(
        "--no-lead-mutation",
        action="store_true",
        help="Do not delete reply EmailEvents or reset leads (use with full reset).",
    )
    args = p.parse_args()

    if args.unibox_only and args.imap_only:
        print("ERROR: Choose at most one of --unibox-only and --imap-only.")
        sys.exit(1)

    engine = _engine()
    SessionLocal = sessionmaker(bind=engine)
    db: Session = SessionLocal()
    try:
        if args.list_workspaces:
            list_workspaces(db)
            return
        wid = resolve_workspace_id(db, args)
        run_reset(db, wid, args)
    finally:
        db.close()


if __name__ == "__main__":
    main()
