"""
workers/engine_loops.py — Background loops for sending, warmup, and IMAP reply scans.
"""

import asyncio
import os

from app.database import SessionLocal
from app.services import sending_engine_service


SEND_LOOP_SECONDS = int(os.environ.get("SEND_LOOP_SECONDS", "5"))
SEND_BATCH_SIZE = int(os.environ.get("SEND_BATCH_SIZE", "20"))
WARMUP_LOOP_SECONDS = int(os.environ.get("WARMUP_LOOP_SECONDS", "900"))
IMAP_LOOP_SECONDS = int(os.environ.get("IMAP_LOOP_SECONDS", "120"))


async def sending_loop():
    while True:
        try:
            with SessionLocal() as db:
                claims = sending_engine_service.claim_queued_leads(SEND_BATCH_SIZE, db)
            for lead_id, token in claims:
                with SessionLocal() as db:
                    sending_engine_service.process_claimed_lead(lead_id, token, db)
        except Exception:
            # Keep loop alive; failures are persisted per-lead where possible.
            pass
        await asyncio.sleep(SEND_LOOP_SECONDS)


async def warmup_loop():
    while True:
        try:
            with SessionLocal() as db:
                sending_engine_service.run_warmup_iteration(db)
        except Exception:
            pass
        await asyncio.sleep(WARMUP_LOOP_SECONDS)


async def imap_reply_loop():
    while True:
        try:
            with SessionLocal() as db:
                sending_engine_service.run_imap_reply_iteration(db)
        except Exception:
            pass
        await asyncio.sleep(IMAP_LOOP_SECONDS)
