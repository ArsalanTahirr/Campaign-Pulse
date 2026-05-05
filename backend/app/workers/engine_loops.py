"""
workers/engine_loops.py — Background loops for sending, warmup, and IMAP reply scans.
"""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.database import SessionLocal
from app.services import sending_engine_service


SEND_LOOP_SECONDS = int(os.environ.get("SEND_LOOP_SECONDS", "5"))
SEND_BATCH_SIZE = int(os.environ.get("SEND_BATCH_SIZE", "20"))
WARMUP_LOOP_SECONDS = int(os.environ.get("WARMUP_LOOP_SECONDS", "900"))
IMAP_LOOP_SECONDS = int(os.environ.get("IMAP_LOOP_SECONDS", "120"))
_ENGINE_ENABLED = os.environ.get("ENABLE_SENDING_ENGINE", "false").lower() == "true"
SEND_WORKER_COUNT = 4


def is_engine_enabled() -> bool:
    return _ENGINE_ENABLED


def set_engine_enabled(enabled: bool) -> None:
    global _ENGINE_ENABLED
    _ENGINE_ENABLED = bool(enabled)


async def sending_loop():
    while True:
        try:
            if is_engine_enabled():
                with SessionLocal() as db:
                    claims = sending_engine_service.claim_queued_leads(SEND_BATCH_SIZE, db)
                if claims:
                    with ThreadPoolExecutor(max_workers=SEND_WORKER_COUNT) as executor:
                        futures = []
                        for lead_id, token, sender_id in claims:
                            futures.append(
                                executor.submit(
                                    _process_claim_in_worker,
                                    lead_id,
                                    token,
                                    sender_id,
                                )
                            )
                        for fut in as_completed(futures):
                            fut.result()
        except Exception:
            # Keep loop alive; failures are persisted per-lead where possible.
            pass
        await asyncio.sleep(SEND_LOOP_SECONDS)


def _process_claim_in_worker(lead_id: str, token: str, sender_id: str) -> None:
    with SessionLocal() as db:
        sending_engine_service.process_claimed_lead(lead_id, token, sender_id, db)


async def warmup_loop():
    while True:
        try:
            if is_engine_enabled():
                with SessionLocal() as db:
                    sending_engine_service.run_warmup_iteration(db)
        except Exception:
            pass
        await asyncio.sleep(WARMUP_LOOP_SECONDS)


async def imap_reply_loop():
    while True:
        try:
            if is_engine_enabled():
                from app.models import SenderAccount
                from app.services.unibox import ingestion_service

                # Ingest first (parallel accounts, isolated sessions). Header prefetch
                # inside ingest skips full downloads for non-lead mail.
                with SessionLocal() as db:
                    account_ids = [
                        row[0]
                        for row in db.query(SenderAccount.account_id)
                        .filter(
                            SenderAccount.imap_host.isnot(None),
                            SenderAccount.imap_port.isnot(None),
                            SenderAccount.app_password.isnot(None),
                            SenderAccount.status.in_(("active", "warming_up")),
                            SenderAccount.deleted_at.is_(None),
                        )
                        .all()
                    ]
                try:
                    ingestion_service.ingest_accounts_parallel(account_ids)
                except Exception:
                    pass

                # Warmup spam rescue (reply detection is handled in ingestion only).
                with SessionLocal() as db:
                    sending_engine_service.run_imap_reply_iteration(db)
        except Exception:
            pass
        await asyncio.sleep(IMAP_LOOP_SECONDS)
