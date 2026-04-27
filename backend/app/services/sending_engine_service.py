"""
services/sending_engine_service.py — Core sending, warmup, and reply-detection engine.
"""

import imaplib
import math
import os
import smtplib
import ssl
import uuid
from datetime import datetime, time, timedelta, timezone
from email.message import EmailMessage
from email.utils import parseaddr
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Campaign,
    CampaignSenderPool,
    EmailEvent,
    Lead,
    SenderAccount,
    SequenceStep,
    StepEmail,
    WarmupSettings,
)
from app.services.tracking_service import sign_click_target

TRACKING_BASE_URL = os.environ.get("TRACKING_BASE_URL", "http://localhost:8000")


def _effective_daily_limit(account: SenderAccount) -> int:
    warm = account.warmup_settings
    if not warm or not warm.is_warmup_active:
        return account.daily_sending_limit

    base = max(float(warm.start_mail_rate), 0.0)
    ramp = max(float(warm.ramp_up_rate), 1.0)
    start_at = warm.warmup_started_at or datetime.now(timezone.utc)
    days = max((datetime.now(timezone.utc).date() - start_at.date()).days, 0)
    ramped = base * (ramp ** days)
    warm_cap = min(math.floor(ramped), int(warm.daily_max_emails))
    return max(1, min(account.daily_sending_limit, warm_cap))


def select_next_sender_account(campaign_id: str, db: Session) -> SenderAccount | None:
    rows = (
        db.query(SenderAccount)
        .join(CampaignSenderPool, CampaignSenderPool.sender_account_id == SenderAccount.account_id)
        .outerjoin(WarmupSettings, WarmupSettings.account_id == SenderAccount.account_id)
        .options(joinedload(SenderAccount.warmup_settings))
        .filter(
            CampaignSenderPool.campaign_id == campaign_id,
            SenderAccount.status.in_(("active", "warming_up")),
            SenderAccount.deleted_at.is_(None),
            SenderAccount.is_verified.is_(True),
        )
        .order_by(SenderAccount.last_used_at.asc().nullsfirst(), SenderAccount.account_id.asc())
        .all()
    )
    for account in rows:
        if account.sent_count_today < _effective_daily_limit(account):
            return account
    return None


def _parse_send_time(send_time_value: str | None, tz_name: str) -> datetime:
    now_local = datetime.now(ZoneInfo(tz_name))
    if not send_time_value:
        return now_local
    hh, mm = send_time_value.split(":")
    scheduled_local = datetime.combine(now_local.date(), time(int(hh), int(mm)), tzinfo=ZoneInfo(tz_name))
    if scheduled_local < now_local:
        scheduled_local = scheduled_local + timedelta(days=1)
    return scheduled_local


def _next_step_schedule_utc(campaign: Campaign, step: SequenceStep, base_utc: datetime) -> datetime:
    tz_name = campaign.timezone or "UTC"
    base_local = base_utc.astimezone(ZoneInfo(tz_name))
    candidate_local = _parse_send_time(step.send_time, tz_name)
    candidate_local = candidate_local + timedelta(days=max(step.wait_days, 0))

    if step.send_days:
        allowed = {str(d).lower() for d in step.send_days}
        for _ in range(14):
            if candidate_local.strftime("%A").lower() in allowed:
                break
            candidate_local = candidate_local + timedelta(days=1)

    if candidate_local < base_local:
        candidate_local = base_local
    return candidate_local.astimezone(timezone.utc)


def _pick_step_variant(step_id: str, db: Session) -> StepEmail | None:
    return (
        db.query(StepEmail)
        .filter(StepEmail.step_id == step_id)
        .order_by(StepEmail.created_at.asc())
        .first()
    )


def _append_tracking_pixel(html_body: str, sent_event_id: str) -> str:
    pixel_url = f"{TRACKING_BASE_URL}/track/open/{sent_event_id}"
    pixel_tag = f'<img src="{pixel_url}" alt="" width="1" height="1" style="display:none;" />'
    return f"{html_body}\n{pixel_tag}"


def build_tracked_click_url(sent_event_id: str, target_url: str) -> str:
    sig = sign_click_target(sent_event_id, target_url)
    from urllib.parse import quote

    return f"{TRACKING_BASE_URL}/track/click/{sent_event_id}?u={quote(target_url, safe='')}&sig={sig}"


def _send_smtp(account: SenderAccount, recipient: str, subject: str, html_body: str, plain_body: str = "") -> str:
    if not account.smtp_host or not account.smtp_port or not account.app_password:
        raise RuntimeError("Sender account SMTP configuration is incomplete.")

    message = EmailMessage()
    message["From"] = account.email
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(plain_body or "This email contains HTML content.")
    message.add_alternative(html_body, subtype="html")
    message_id = message["Message-ID"] or f"<{uuid.uuid4()}@campaignpulse.local>"
    message["Message-ID"] = message_id

    try:
        if int(account.smtp_port) == 465:
            with smtplib.SMTP_SSL(account.smtp_host, int(account.smtp_port), timeout=30) as server:
                server.login(account.email, account.app_password)
                server.send_message(message)
        else:
            context = ssl.create_default_context()
            with smtplib.SMTP(account.smtp_host, int(account.smtp_port), timeout=30) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(account.email, account.app_password)
                server.send_message(message)
    except Exception as exc:
        raise RuntimeError(f"SMTP send failed for {account.email}: {exc}") from exc

    return message_id


def claim_queued_leads(batch_size: int, db: Session) -> list[tuple[str, str]]:
    now = datetime.now(timezone.utc)
    leads = (
        db.query(Lead)
        .join(Campaign, Campaign.campaign_id == Lead.campaign_id)
        .filter(
            Campaign.status == "active",
            Lead.lead_status == "active",
            Lead.delivery_state == "queued",
            Lead.next_scheduled_at.isnot(None),
            Lead.next_scheduled_at <= now,
        )
        .order_by(Lead.next_scheduled_at.asc())
        .with_for_update(skip_locked=True)
        .limit(batch_size)
        .all()
    )
    claims: list[tuple[str, str]] = []
    for lead in leads:
        token = str(uuid.uuid4())
        lead.delivery_state = "sending"
        lead.lock_token = token
        lead.locked_at = now
        claims.append((lead.lead_id, token))
    db.commit()
    return claims


def _resolve_current_step(lead: Lead, db: Session) -> SequenceStep | None:
    if lead.next_step_id:
        return db.query(SequenceStep).filter(SequenceStep.step_id == lead.next_step_id).first()
    return (
        db.query(SequenceStep)
        .filter(SequenceStep.campaign_id == lead.campaign_id)
        .order_by(SequenceStep.step_number.asc())
        .first()
    )


def _resolve_followup_step(current_step: SequenceStep, db: Session) -> SequenceStep | None:
    return (
        db.query(SequenceStep)
        .filter(
            SequenceStep.campaign_id == current_step.campaign_id,
            SequenceStep.step_number > current_step.step_number,
        )
        .order_by(SequenceStep.step_number.asc())
        .first()
    )


def initialize_lead_schedule(lead: Lead, db: Session) -> None:
    first_step = (
        db.query(SequenceStep)
        .filter(SequenceStep.campaign_id == lead.campaign_id)
        .order_by(SequenceStep.step_number.asc())
        .first()
    )
    if not first_step:
        lead.next_step_id = None
        lead.next_scheduled_at = None
        return
    campaign = db.query(Campaign).filter(Campaign.campaign_id == lead.campaign_id).first()
    lead.next_step_id = first_step.step_id
    lead.next_scheduled_at = _next_step_schedule_utc(
        campaign=campaign,
        step=first_step,
        base_utc=datetime.now(timezone.utc),
    )


def process_claimed_lead(lead_id: str, lock_token: str, db: Session) -> None:
    now = datetime.now(timezone.utc)
    lead = (
        db.query(Lead)
        .options(joinedload(Lead.campaign))
        .filter(
            Lead.lead_id == lead_id,
            Lead.lock_token == lock_token,
            Lead.delivery_state == "sending",
        )
        .first()
    )
    if not lead:
        return

    current_step = _resolve_current_step(lead, db)
    if not current_step:
        lead.delivery_state = "sent"
        lead.lock_token = None
        lead.locked_at = None
        lead.next_step_id = None
        lead.next_scheduled_at = None
        db.commit()
        return

    variant = _pick_step_variant(current_step.step_id, db)
    if not variant:
        lead.delivery_state = "failed"
        lead.lock_token = None
        lead.locked_at = None
        db.commit()
        return

    sender = select_next_sender_account(lead.campaign_id, db)
    if not sender:
        lead.delivery_state = "queued"
        lead.lock_token = None
        lead.locked_at = None
        lead.next_scheduled_at = now + timedelta(minutes=10)
        db.commit()
        return

    sent_event_id = str(uuid.uuid4())
    html_body = _append_tracking_pixel(variant.email_body, sent_event_id)
    try:
        message_id = _send_smtp(
            account=sender,
            recipient=lead.email,
            subject=variant.subject_line,
            html_body=html_body,
        )
    except Exception as exc:
        lead.delivery_state = "failed"
        lead.lock_token = None
        lead.locked_at = None
        db.add(
            EmailEvent(
                lead_id=lead.lead_id,
                step_id=current_step.step_id,
                event_type="failed",
                event_scope="lead",
                sender_account_id=sender.account_id,
                occurred_at=now,
                event_metadata={"error": str(exc)},
            )
        )
        db.commit()
        return

    db.add(
        EmailEvent(
            event_id=sent_event_id,
            lead_id=lead.lead_id,
            step_id=current_step.step_id,
            event_type="sent",
            event_scope="lead",
            sender_account_id=sender.account_id,
            occurred_at=now,
            event_metadata={"message_id": message_id},
        )
    )
    sender.sent_count_today = int(sender.sent_count_today or 0) + 1
    sender.last_used_at = now

    next_step = _resolve_followup_step(current_step, db)
    if next_step:
        lead.next_step_id = next_step.step_id
        lead.next_scheduled_at = _next_step_schedule_utc(lead.campaign, next_step, now)
        lead.delivery_state = "queued"
    else:
        lead.next_step_id = None
        lead.next_scheduled_at = None
        lead.delivery_state = "sent"

    lead.lock_token = None
    lead.locked_at = None
    db.commit()


def run_warmup_iteration(db: Session) -> int:
    accounts = (
        db.query(SenderAccount)
        .options(joinedload(SenderAccount.warmup_settings))
        .filter(
            SenderAccount.status.in_(("active", "warming_up")),
            SenderAccount.deleted_at.is_(None),
            SenderAccount.is_verified.is_(True),
            SenderAccount.smtp_host.isnot(None),
            SenderAccount.smtp_port.isnot(None),
            SenderAccount.app_password.isnot(None),
        )
        .all()
    )

    by_workspace: dict[str, list[SenderAccount]] = {}
    for acc in accounts:
        if not acc.warmup_settings or not acc.warmup_settings.is_warmup_active:
            continue
        by_workspace.setdefault(acc.workspace_id, []).append(acc)

    sent = 0
    now = datetime.now(timezone.utc)
    for workspace_accounts in by_workspace.values():
        if len(workspace_accounts) < 2:
            continue
        for idx, sender in enumerate(workspace_accounts):
            recipient = workspace_accounts[(idx + 1) % len(workspace_accounts)]
            if sender.sent_count_today >= _effective_daily_limit(sender):
                continue
            thread_id = str(uuid.uuid4())
            try:
                message_id = _send_smtp(
                    account=sender,
                    recipient=recipient.email,
                    subject="Warmup connection",
                    html_body="<p>Warmup check-in message.</p>",
                    plain_body="Warmup check-in message.",
                )
            except Exception as exc:
                db.add(
                    EmailEvent(
                        event_scope="warmup",
                        event_type="failed",
                        sender_account_id=sender.account_id,
                        recipient_account_id=recipient.account_id,
                        warmup_thread_id=thread_id,
                        occurred_at=now,
                        event_metadata={"error": str(exc)},
                    )
                )
                continue

            db.add(
                EmailEvent(
                    event_scope="warmup",
                    event_type="sent",
                    sender_account_id=sender.account_id,
                    recipient_account_id=recipient.account_id,
                    warmup_thread_id=thread_id,
                    occurred_at=now,
                    event_metadata={"message_id": message_id},
                )
            )
            sender.sent_count_today = int(sender.sent_count_today or 0) + 1
            sender.last_used_at = now
            sent += 1
    db.commit()
    return sent


def run_imap_reply_iteration(db: Session) -> int:
    processed = 0
    accounts = (
        db.query(SenderAccount)
        .filter(
            SenderAccount.imap_host.isnot(None),
            SenderAccount.imap_port.isnot(None),
            SenderAccount.app_password.isnot(None),
            SenderAccount.status.in_(("active", "warming_up")),
            SenderAccount.deleted_at.is_(None),
        )
        .all()
    )
    for account in accounts:
        try:
            with imaplib.IMAP4_SSL(account.imap_host, int(account.imap_port)) as client:
                client.login(account.email, account.app_password)
                client.select("INBOX")
                start_uid = int(account.last_imap_uid or 0) + 1
                status_value, data = client.uid("SEARCH", None, f"UID {start_uid}:*")
                if status_value != "OK":
                    continue
                uid_values = [u.decode("utf-8") for u in (data[0] or b"").split()][: int(account.max_imap_fetch or 100)]
                max_seen_uid = int(account.last_imap_uid or 0)
                for uid in uid_values:
                    status_fetch, msg_data = client.uid("FETCH", uid, "(BODY.PEEK[HEADER.FIELDS (FROM)])")
                    if status_fetch != "OK" or not msg_data:
                        continue
                    header_bytes = msg_data[0][1] if isinstance(msg_data[0], tuple) else b""
                    header_text = header_bytes.decode("utf-8", errors="ignore")
                    from_email = parseaddr(header_text.replace("From:", "").strip())[1].lower()
                    if not from_email:
                        continue

                    lead = (
                        db.query(Lead)
                        .join(EmailEvent, EmailEvent.lead_id == Lead.lead_id)
                        .filter(
                            func.lower(Lead.email) == from_email,
                            EmailEvent.event_type == "sent",
                            EmailEvent.sender_account_id == account.account_id,
                        )
                        .order_by(EmailEvent.occurred_at.desc())
                        .first()
                    )
                    if not lead:
                        max_seen_uid = max(max_seen_uid, int(uid))
                        continue

                    db.add(
                        EmailEvent(
                            lead_id=lead.lead_id,
                            event_type="replied",
                            event_scope="lead",
                            sender_account_id=account.account_id,
                            occurred_at=datetime.now(timezone.utc),
                            event_metadata={"imap_uid": uid},
                        )
                    )
                    lead.lead_status = "replied"
                    lead.delivery_state = "paused"
                    max_seen_uid = max(max_seen_uid, int(uid))
                    processed += 1

                account.last_imap_uid = max_seen_uid or account.last_imap_uid
                db.commit()
        except Exception:
            # Robust polling loop: skip account-level IMAP failures and continue.
            db.rollback()
            continue
    return processed

