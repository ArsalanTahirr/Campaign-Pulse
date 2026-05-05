"""
services/sending_engine_service.py — Core sending, warmup, and reply-detection engine.
"""

import imaplib
import math
import os
import random
import re
import smtplib
import ssl
import time
import uuid
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone
from datetime import time as dt_time
from email.header import decode_header
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from zoneinfo import ZoneInfo

from sqlalchemy import func
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

def _resolved_tracking_base_url() -> str:
    raw = (os.environ.get("TRACKING_BASE_URL", "http://localhost:8000") or "").strip()
    if not raw:
        return "http://localhost:8000"
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    is_local = host in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme == "http" and not is_local:
        return raw.replace("http://", "https://", 1)
    return raw


TRACKING_BASE_URL = _resolved_tracking_base_url()
MERGE_TAG_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
# Socket read timeout for IMAP (avoids hung HTTP requests when a server stops responding).
IMAP_SOCKET_TIMEOUT = int(os.environ.get("IMAP_SOCKET_TIMEOUT", "90"))
# Batch OR(FROM…) searches so global warmup pools don’t issue hundreds of SEARCH commands per folder.
_IMAP_FROM_SEARCH_CHUNK = int(os.environ.get("IMAP_WARMUP_FROM_SEARCH_CHUNK", "12"))
# How many messages per UID FETCH round-trip (SUBJECT/FROM header peek).
_IMAP_FETCH_BATCH = int(os.environ.get("IMAP_FETCH_BATCH", "40"))

# Peer warmup: randomized professional copy (subject + html + plain). Keep subjects unique for IMAP rescue matching.
WARMUP_MESSAGE_PAIRS: list[tuple[str, str, str]] = [
    (
        "Quick sync on next steps",
        "<p>Hi — when you have a moment, could we do a quick sync on next steps?</p>",
        "Hi — when you have a moment, could we do a quick sync on next steps?",
    ),
    (
        "Following up on our last note",
        "<p>Just following up on our last note — let me know if today still works on your side.</p>",
        "Just following up on our last note — let me know if today still works on your side.",
    ),
    (
        "Question about the shared doc",
        "<p>I had a small question about the shared doc — happy to jump on a short call if easier.</p>",
        "I had a small question about the shared doc — happy to jump on a short call if easier.",
    ),
    (
        "Circling back on the timeline",
        "<p>Circling back on the timeline we discussed — any updates from your team?</p>",
        "Circling back on the timeline we discussed — any updates from your team?",
    ),
    (
        "Quick check-in before Friday",
        "<p>Quick check-in before Friday — want to make sure we’re aligned on deliverables.</p>",
        "Quick check-in before Friday — want to make sure we're aligned on deliverables.",
    ),
    (
        "Thanks for the update",
        "<p>Thanks for the update earlier — this looks good from my side.</p>",
        "Thanks for the update earlier — this looks good from my side.",
    ),
    (
        "Availability for a brief call",
        "<p>Do you have 15 minutes tomorrow for a brief call? I can send a calendar invite.</p>",
        "Do you have 15 minutes tomorrow for a brief call? I can send a calendar invite.",
    ),
    (
        "Sharing a quick thought",
        "<p>Sharing a quick thought on the approach we talked about — open to your feedback.</p>",
        "Sharing a quick thought on the approach we talked about — open to your feedback.",
    ),
    (
        "Looping in on the decision",
        "<p>Looping you in on the decision — no rush, whenever you can take a look.</p>",
        "Looping you in on the decision — no rush, whenever you can take a look.",
    ),
    (
        "Minor edit to the draft",
        "<p>I made a minor edit to the draft — feel free to comment when you get a chance.</p>",
        "I made a minor edit to the draft — feel free to comment when you get a chance.",
    ),
    (
        "Confirming receipt",
        "<p>Confirming receipt of your last message — I’ll follow up with details shortly.</p>",
        "Confirming receipt of your last message — I'll follow up with details shortly.",
    ),
    (
        "Next week’s planning",
        "<p>For next week’s planning, are we still targeting the same milestone?</p>",
        "For next week's planning, are we still targeting the same milestone?",
    ),
]

WARMUP_SUBJECTS_LOWER: frozenset[str] = frozenset(s.lower() for s, _, _ in WARMUP_MESSAGE_PAIRS)

_SPAM_FOLDER_CANDIDATES: tuple[str, ...] = (
    "[Gmail]/Spam",
    "Spam",
    "Junk",
    "Junk E-mail",
    "Bulk Mail",
)


def _pick_warmup_message() -> tuple[str, str, str]:
    return random.choice(WARMUP_MESSAGE_PAIRS)


def _warmup_decode_subject_header(raw: str) -> str:
    parts = decode_header((raw or "").strip())
    chunks: list[str] = []
    for part, charset in parts:
        if isinstance(part, bytes):
            chunks.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            chunks.append(str(part))
    return "".join(chunks).strip()


def _warmup_subject_normalized_for_match(raw: str) -> str:
    s = _warmup_decode_subject_header(raw)
    while True:
        low = s.lower()
        if low.startswith("re:"):
            s = s[3:].strip()
        elif low.startswith("fwd:"):
            s = s[4:].strip()
        elif low.startswith("fw:"):
            s = s[3:].strip()
        else:
            break
    return s.strip().lower()


def _warmup_subject_matches_known(subject_header_value: str) -> bool:
    return _warmup_subject_normalized_for_match(subject_header_value) in WARMUP_SUBJECTS_LOWER


def _imap_quote_addr(addr: str) -> str:
    return addr.replace("\\", "\\\\").replace('"', '\\"')


def _imap_search_criterion_from_any(peers: list[str]) -> str:
    """IMAP SEARCH criterion: match if From is any of the quoted addresses (nested OR)."""
    esc = [_imap_quote_addr(p) for p in peers]
    if len(esc) == 1:
        return f'(FROM "{esc[0]}")'
    tail = f'(FROM "{esc[-1]}")'
    for i in range(len(esc) - 2, -1, -1):
        tail = f'(OR (FROM "{esc[i]}") {tail})'
    return tail


def _imap_uid_search_from_peer_chunks(client: imaplib.IMAP4_SSL, peers: list[str]) -> set[str]:
    """Union UID SEARCH results; peers chunked to keep each SEARCH criterion small."""
    uid_set: set[str] = set()
    if not peers:
        return uid_set
    chunk = max(1, _IMAP_FROM_SEARCH_CHUNK)
    for i in range(0, len(peers), chunk):
        part = peers[i : i + chunk]
        try:
            crit = _imap_search_criterion_from_any(part)
            st, data = client.uid("SEARCH", None, crit)
            if st != "OK" or not data or not data[0]:
                continue
            for u in (data[0] or b"").split():
                uid_set.add(u.decode("utf-8"))
        except Exception:
            continue
    return uid_set


def _header_block_folded_subject(header_text: str) -> str:
    """Parse Subject value from a HEADER.FIELDS (SUBJECT) block (handles folded lines)."""
    subj_parts: list[str] = []
    in_subj = False
    for raw_line in header_text.splitlines():
        line = raw_line.rstrip("\r")
        if line.lower().startswith("subject:"):
            subj_parts.append(line.split(":", 1)[1].strip())
            in_subj = True
        elif in_subj and line and line[0] in " \t":
            subj_parts.append(" " + line.strip())
        elif in_subj:
            break
    return "".join(subj_parts)


def _imap_batch_fetch_uid_header_fields(
    client: imaplib.IMAP4_SSL,
    uids: list[str],
    header_field_names: str,
) -> dict[str, bytes]:
    """
    Batch UID FETCH for BODY.PEEK[HEADER.FIELDS (...)].
    `header_field_names` e.g. \"SUBJECT\" or \"FROM\". Falls back to per-UID FETCH when needed.
    """
    out: dict[str, bytes] = {}
    if not uids:
        return out
    fetch_item = f"(BODY.PEEK[HEADER.FIELDS ({header_field_names})])"
    batch = max(1, _IMAP_FETCH_BATCH)

    def fetch_one(uid: str) -> None:
        if uid in out:
            return
        try:
            st, msg_data = client.uid("FETCH", uid, fetch_item)
            if st != "OK" or not msg_data:
                return
            for part in msg_data:
                if isinstance(part, tuple) and len(part) >= 2:
                    _meta, payload = part[0], part[1]
                    if isinstance(payload, bytes):
                        out[uid] = payload
                    return
        except Exception:
            return

    for i in range(0, len(uids), batch):
        chunk = uids[i : i + batch]
        uid_spec = ",".join(chunk)
        try:
            st, data = client.uid("FETCH", uid_spec, fetch_item)
            if st == "OK" and data:
                for part in data:
                    if isinstance(part, tuple) and len(part) >= 2:
                        meta, payload = part[0], part[1]
                        meta_b = meta if isinstance(meta, bytes) else str(meta).encode("utf-8", errors="replace")
                        m = re.search(rb"UID (\d+)", meta_b)
                        if m and isinstance(payload, bytes):
                            out[m.group(1).decode("ascii")] = payload
        except Exception:
            pass
        for u in chunk:
            if u not in out:
                fetch_one(u)
    return out


def _imap_try_select_mailbox(client: imaplib.IMAP4_SSL, mailbox: str) -> bool:
    """Try SELECT with and without quoting (providers differ)."""
    candidates = [mailbox]
    if " " in mailbox and not (mailbox.startswith('"') and mailbox.endswith('"')):
        candidates.insert(0, f'"{mailbox}"')
    for mbox in candidates:
        try:
            typ, _ = client.select(mbox)
            if typ == "OK":
                return True
        except Exception:
            continue
    return False


def _imap_rescue_warmup_spam_on_client(
    client: imaplib.IMAP4_SSL,
    account: SenderAccount,
    peer_emails_lower: set[str],
) -> None:
    """
    Move messages in Spam/Junk from other global warmup-pool senders (matching known subjects) into INBOX.
    Caller must have already authenticated `client`. Leaves the session authenticated; caller should SELECT INBOX after.
    """
    if not peer_emails_lower:
        return

    try:
        self_lower = (account.email or "").lower()
        peers_excl = sorted(p for p in peer_emails_lower if p != self_lower)
        if not peers_excl:
            return

        for spam_folder in _SPAM_FOLDER_CANDIDATES:
            if not _imap_try_select_mailbox(client, spam_folder):
                continue

            uid_set = _imap_uid_search_from_peer_chunks(client, peers_excl)
            sorted_uids = sorted(uid_set, key=lambda x: int(x) if x.isdigit() else 0)
            subj_by_uid = _imap_batch_fetch_uid_header_fields(client, sorted_uids, "SUBJECT")

            to_move: list[str] = []
            for uid in sorted_uids:
                blob = subj_by_uid.get(uid)
                if not blob:
                    continue
                subj_line = _header_block_folded_subject(blob.decode("utf-8", errors="ignore"))
                if _warmup_subject_matches_known(subj_line):
                    to_move.append(uid)

            for uid in to_move:
                try:
                    st, _ = client.uid("COPY", uid, "INBOX")
                    if st == "OK":
                        client.uid("STORE", uid, "+FLAGS", "\\Deleted")
                except Exception:
                    continue
            if to_move:
                try:
                    client.expunge()
                except Exception:
                    pass

            try:
                client.close()
            except Exception:
                pass
            # One junk mailbox per account in practice; avoids extra SELECT attempts.
            break
    except Exception:
        return


def _imap_rescue_warmup_spam_to_inbox(
    account: SenderAccount,
    peer_emails_lower: set[str],
) -> None:
    """
    Open IMAP for `account` and run global-pool spam rescue (same peer set as warmup sends).
    """
    if not account.imap_host or not account.imap_port or not account.app_password:
        return
    if not peer_emails_lower:
        return

    try:
        with imaplib.IMAP4_SSL(
            account.imap_host, int(account.imap_port), timeout=IMAP_SOCKET_TIMEOUT
        ) as client:
            client.login(account.email, account.app_password)
            _imap_rescue_warmup_spam_on_client(client, account, peer_emails_lower)
    except Exception:
        return


def load_global_warmup_pool(db: Session) -> list[SenderAccount]:
    """All verified senders with SMTP + app password and warmup active — global pool (any workspace)."""
    rows = (
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
    return [acc for acc in rows if acc.warmup_settings and acc.warmup_settings.is_warmup_active]


def global_warmup_peer_emails_lower(pool: list[SenderAccount]) -> set[str]:
    return {(a.email or "").lower() for a in pool if a.email}


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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _sender_jitter_bounds_seconds() -> tuple[int, int]:
    lo = int(os.environ.get("SENDER_READY_JITTER_MIN_SECONDS", "120"))
    hi = int(os.environ.get("SENDER_READY_JITTER_MAX_SECONDS", "300"))
    if lo < 0:
        lo = 0
    if hi < lo:
        hi = lo
    return lo, hi


def _next_sender_ready_at(now_utc: datetime) -> datetime:
    lo, hi = _sender_jitter_bounds_seconds()
    return now_utc + timedelta(seconds=random.randint(lo, hi))


def select_next_sender_account(campaign_id: str, db: Session) -> tuple[SenderAccount | None, datetime | None]:
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
    now = datetime.now(timezone.utc)
    earliest_next_available_at: datetime | None = None
    skipped_warmup = 0
    skipped_delay = 0
    skipped_daily_limit = 0
    for account in rows:
        # Warmup-active accounts are reserved for warmup traffic, not campaign sends.
        warmup_active = bool(
            account.warmup_settings and getattr(account.warmup_settings, "is_warmup_active", False)
        )
        if warmup_active:
            skipped_warmup += 1
            continue
        min_delay_seconds = max(int(account.min_delay_seconds or 0), 0)
        if account.last_used_at is not None:
            next_allowed_at = account.last_used_at + timedelta(seconds=min_delay_seconds)
            if now < next_allowed_at:
                skipped_delay += 1
                if earliest_next_available_at is None or next_allowed_at < earliest_next_available_at:
                    earliest_next_available_at = next_allowed_at
                continue
        if account.sent_count_today < _effective_daily_limit(account):
            return account, now
        skipped_daily_limit += 1
    return None, earliest_next_available_at


def _hhmm_to_time(hhmm: str) -> dt_time:
    hh, mm = hhmm.split(":")
    return dt_time(int(hh), int(mm))


def _send_window_end_str(step: SequenceStep) -> str | None:
    if not step.send_time:
        return None
    return step.send_window_end or step.send_time


def _send_window_bounds_on_date(
    step: SequenceStep,
    tz: ZoneInfo,
    on_date: datetime.date,
) -> tuple[datetime, datetime] | None:
    """
    Inclusive daily window [lo, hi] in `tz`. None if step has no send_time (whole day used elsewhere).

    When start and end are the same HH:MM, this is a single *slot* (that whole minute), not a 24-hour
    window — same as typical ESP "send at this time" behavior. For an all-day window use 00:00–23:59.
    """
    if not step.send_time:
        return None
    end_s = _send_window_end_str(step)
    if not end_s:
        return None
    lo = datetime.combine(on_date, _hhmm_to_time(step.send_time), tzinfo=tz)
    hi = datetime.combine(on_date, _hhmm_to_time(end_s), tzinfo=tz)
    if hi < lo:
        return None
    if hi == lo:
        hi = lo + timedelta(minutes=1) - timedelta(microseconds=1)
    return lo, hi


def _next_step_schedule_utc(campaign: Campaign, step: SequenceStep, base_utc: datetime) -> datetime:
    """
    Earliest UTC time >= base_utc on an allowed send day, inside [send_time, send_window_end]
    in the campaign timezone (inclusive end). send_window_end null => same as send_time (one-minute slot).

    Same start/end is not a 24h window; use 00:00 start and 23:59 end for all-day on that date.
    """
    tz = ZoneInfo(campaign.timezone or "UTC")
    base_local = base_utc.astimezone(tz)
    wait = max(int(step.wait_days or 0), 0)
    allowed = {str(d).lower() for d in step.send_days} if step.send_days else None

    first_calendar_day = base_local.date() + timedelta(days=wait)

    for day_offset in range(0, 56):
        d = first_calendar_day + timedelta(days=day_offset)
        if allowed and d.strftime("%A").lower() not in allowed:
            continue

        bounds = _send_window_bounds_on_date(step, tz, d)
        if bounds is None:
            lo = datetime.combine(d, dt_time(0, 0), tzinfo=tz)
            hi = datetime.combine(d, dt_time(23, 59, 59), tzinfo=tz)
        else:
            lo, hi = bounds

        cand = max(lo, base_local)
        if cand <= hi:
            return cand.astimezone(timezone.utc)

    return base_utc


def _is_within_step_send_window(campaign: Campaign, step: SequenceStep, when_utc: datetime) -> bool:
    """True if when_utc falls on an allowed send day and inside the step's local send window."""
    tz = ZoneInfo(campaign.timezone or "UTC")
    local = when_utc.astimezone(tz)
    if step.send_days:
        allowed = {str(x).lower() for x in step.send_days}
        if local.strftime("%A").lower() not in allowed:
            return False
    bounds = _send_window_bounds_on_date(step, tz, local.date())
    if bounds is None:
        return True
    lo, hi = bounds
    return lo <= local <= hi


def _pick_step_variant(step_id: str, db: Session) -> StepEmail | None:
    return (
        db.query(StepEmail)
        .filter(StepEmail.step_id == step_id)
        .order_by(StepEmail.created_at.asc())
        .first()
    )


def _pick_step_variant_for_lead(step_id: str, lead_id: str, db: Session) -> tuple[StepEmail | None, int, int]:
    variants = (
        db.query(StepEmail)
        .filter(StepEmail.step_id == step_id)
        .order_by(StepEmail.created_at.asc())
        .all()
    )
    total = len(variants)
    if total == 0:
        return None, 0, 0
    sent_count = (
        db.query(func.count(EmailEvent.event_id))
        .filter(
            EmailEvent.lead_id == lead_id,
            EmailEvent.step_id == step_id,
            EmailEvent.event_scope == "lead",
            EmailEvent.event_type == "sent",
        )
        .scalar()
        or 0
    )
    idx = int(sent_count) % total
    return variants[idx], idx, total


def _build_merge_context(lead: Lead) -> dict[str, str]:
    context: dict[str, str] = {
        "email": str(lead.email or ""),
        "first_name": str(lead.first_name or ""),
        "last_name": str(lead.last_name or ""),
    }

    custom_variables = lead.custom_variables if isinstance(lead.custom_variables, dict) else {}
    for key, value in custom_variables.items():
        key_str = str(key).strip()
        if not key_str:
            continue
        context[key_str] = "" if value is None else str(value)

    return context


def _render_merge_tags(template: str, context: dict[str, str]) -> str:
    if not template:
        return ""

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return context.get(key, "")

    return MERGE_TAG_PATTERN.sub(_replace, template)


def _append_tracking_pixel(html_body: str, sent_event_id: str) -> str:
    pixel_url = f"{TRACKING_BASE_URL}/track/open/{sent_event_id}"
    pixel_tag = f'<img src="{pixel_url}" alt="" width="1" height="1" style="display:none;" />'
    return f"{html_body}\n{pixel_tag}"


_HREF_HTTP_RE = re.compile(
    r'(?P<prefix>\bhref\s*=\s*)(?P<q>["\'])(?P<url>https?://[^"\']+)(?P=q)',
    re.IGNORECASE,
)
_BARE_HTTP_RE = re.compile(
    r'(?<!["\'=])(https?://[^\s<>"\']+)',
    re.IGNORECASE,
)


def _rewrite_html_links_for_click_tracking(html: str, sent_event_id: str) -> str:
    """
    Wrap external http(s) anchors in signed /track/click/{sent_event_id} URLs so
    clicks become EmailEvent('clicked') rows. Skips mailto/tel/javascript and
    URLs that are already tracking links.
    """
    if not html or not sent_event_id:
        return html

    def repl(m: re.Match[str]) -> str:
        q = m.group("q")
        url = m.group("url")
        low = url.lower()
        if low.startswith(("mailto:", "tel:", "javascript:")):
            return m.group(0)
        if "/track/click/" in low or "/track/open/" in low:
            return m.group(0)
        tracked = build_tracked_click_url(sent_event_id, url)
        return f'{m.group("prefix")}{q}{tracked}{q}'

    rewritten = _HREF_HTTP_RE.sub(repl, html)
    # Some templates are stored as bare URLs (no anchor tag). Wrap those so
    # email-client auto-linking still goes through tracking.
    def repl_bare(m: re.Match[str]) -> str:
        url = m.group(1)
        low = url.lower()
        if "/track/click/" in low or "/track/open/" in low:
            return url
        tracked = build_tracked_click_url(sent_event_id, url)
        return f'<a href="{tracked}">{url}</a>'

    rewritten = _BARE_HTTP_RE.sub(repl_bare, rewritten)
    return rewritten


def build_tracked_click_url(sent_event_id: str, target_url: str) -> str:
    sig = sign_click_target(sent_event_id, target_url)
    from urllib.parse import quote

    return f"{TRACKING_BASE_URL}/track/click/{sent_event_id}?u={quote(target_url, safe='')}&sig={sig}"


def _send_smtp(
    account: SenderAccount,
    recipient: str,
    subject: str,
    html_body: str,
    plain_body: str = "",
    from_display_name: str | None = None,
) -> str:
    if not account.smtp_host or not account.smtp_port or not account.app_password:
        raise RuntimeError("Sender account SMTP configuration is incomplete.")

    message = EmailMessage()
    display = (from_display_name or "").strip()
    message["From"] = (
        formataddr((display, account.email)) if display else account.email
    )
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(plain_body or "This email contains HTML content.")
    message.add_alternative(html_body, subtype="html")
    message_id = message["Message-ID"] or f"<{uuid.uuid4()}@campaignpulse.local>"
    message["Message-ID"] = message_id
    # Normal-priority + client-like headers (applies to campaign and warmup SMTP).
    message["X-Priority"] = "3"
    message["X-Mailer"] = "Mozilla Thunderbird 115.6.0"
    message["User-Agent"] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Thunderbird/115.6.0"
    )

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


def claim_queued_leads(
    batch_size: int,
    db: Session,
    *,
    workspace_id: str | None = None,
) -> list[tuple[str, str, str]]:
    """
    Claim due queued leads for sending.

    When ``workspace_id`` is set (manual ``run-send-once``), only that workspace
    is considered. When omitted (background ``sending_loop``), any workspace may
    be claimed.
    """
    now = _utcnow()
    sender_q = (
        db.query(SenderAccount)
        .join(CampaignSenderPool, CampaignSenderPool.sender_account_id == SenderAccount.account_id)
        .join(Campaign, Campaign.campaign_id == CampaignSenderPool.campaign_id)
        .filter(
            Campaign.status == "active",
            SenderAccount.status.in_(("active", "warming_up")),
            SenderAccount.deleted_at.is_(None),
            SenderAccount.is_verified.is_(True),
            func.coalesce(SenderAccount.next_ready_at, now) <= now,
        )
    )
    if workspace_id is not None:
        sender_q = sender_q.filter(Campaign.workspace_id == workspace_id)
    sender_rows = (
        sender_q.order_by(
            SenderAccount.next_ready_at.asc().nullsfirst(),
            SenderAccount.last_used_at.asc().nullsfirst(),
            SenderAccount.account_id.asc(),
        )
        .with_for_update(skip_locked=True)
        .limit(batch_size)
        .all()
    )
    ready_senders: list[SenderAccount] = []
    for account in sender_rows:
        warmup_active = bool(
            account.warmup_settings and getattr(account.warmup_settings, "is_warmup_active", False)
        )
        if warmup_active:
            continue
        if int(account.sent_count_today or 0) >= _effective_daily_limit(account):
            continue
        ready_senders.append(account)
    if not ready_senders:
        db.commit()
        return []

    last_sent_at_subq = (
        db.query(func.max(EmailEvent.occurred_at))
        .filter(
            EmailEvent.event_scope == "lead",
            EmailEvent.event_type == "sent",
            EmailEvent.lead_id == Lead.lead_id,
        )
        .correlate(Lead)
        .scalar_subquery()
    )
    lead_q = (
        db.query(Lead)
        .join(Campaign, Campaign.campaign_id == Lead.campaign_id)
        .filter(
            Campaign.status == "active",
            Lead.lead_status == "active",
            Lead.delivery_state == "queued",
            Lead.next_eligible_at.isnot(None),
            Lead.next_eligible_at <= now,
        )
    )
    if workspace_id is not None:
        lead_q = lead_q.filter(Campaign.workspace_id == workspace_id)
    leads = (
        lead_q.order_by(
            Lead.next_eligible_at.asc(),
            last_sent_at_subq.asc().nullsfirst(),
            Lead.campaign_id.asc(),
            Lead.lead_id.asc(),
        )
        .with_for_update(skip_locked=True)
        .limit(len(ready_senders))
        .all()
    )

    claims: list[tuple[str, str, str]] = []
    for sender, lead in zip(ready_senders, leads):
        token = str(uuid.uuid4())
        lead.delivery_state = "sending"
        lead.lock_token = token
        lead.locked_at = now
        claims.append((lead.lead_id, token, sender.account_id))
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
        lead.next_eligible_at = None
        return
    campaign = db.query(Campaign).filter(Campaign.campaign_id == lead.campaign_id).first()
    lead.next_step_id = first_step.step_id
    lead.next_eligible_at = _next_step_schedule_utc(
        campaign=campaign,
        step=first_step,
        base_utc=_utcnow(),
    )


def process_claimed_lead(lead_id: str, lock_token: str, sender_id: str, db: Session) -> None:
    now = _utcnow()
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
        lead.delivery_state = "completed"
        lead.lock_token = None
        lead.locked_at = None
        lead.next_step_id = None
        lead.next_eligible_at = None
        db.commit()
        return

    if not _is_within_step_send_window(lead.campaign, current_step, now):
        lead.delivery_state = "queued"
        lead.lock_token = None
        lead.locked_at = None
        lead.next_eligible_at = _next_step_schedule_utc(lead.campaign, current_step, now)
        db.commit()
        return

    variant, variant_idx, variant_total = _pick_step_variant_for_lead(current_step.step_id, lead.lead_id, db)
    if not variant:
        lead.delivery_state = "failed"
        lead.lock_token = None
        lead.locked_at = None
        db.commit()
        return

    sender = (
        db.query(SenderAccount)
        .options(joinedload(SenderAccount.warmup_settings))
        .filter(
            SenderAccount.account_id == sender_id,
            SenderAccount.status.in_(("active", "warming_up")),
            SenderAccount.deleted_at.is_(None),
            SenderAccount.is_verified.is_(True),
        )
        .first()
    )
    if not sender:
        fallback_at = _next_step_schedule_utc(lead.campaign, current_step, now)
        lead.delivery_state = "queued"
        lead.lock_token = None
        lead.locked_at = None
        lead.next_eligible_at = fallback_at
        db.commit()
        return

    sent_event_id = str(uuid.uuid4())
    merge_context = _build_merge_context(lead)
    rendered_subject = _render_merge_tags(variant.subject_line, merge_context)
    rendered_html_body = _render_merge_tags(variant.email_body, merge_context)

    campaign = lead.campaign
    tracking_on = bool(getattr(campaign, "open_tracking_enabled", True))
    if tracking_on:
        html_body = _rewrite_html_links_for_click_tracking(rendered_html_body, sent_event_id)
        html_body = _append_tracking_pixel(html_body, sent_event_id)
    else:
        html_body = rendered_html_body

    sent_row = EmailEvent(
        event_id=sent_event_id,
        lead_id=lead.lead_id,
        step_id=current_step.step_id,
        event_type="sent",
        event_scope="lead",
        sender_account_id=sender.account_id,
        occurred_at=now,
        event_metadata={},
    )
    db.add(sent_row)
    db.flush()

    try:
        message_id = _send_smtp(
            account=sender,
            recipient=lead.email,
            subject=rendered_subject,
            html_body=html_body,
            from_display_name=variant.from_name,
        )
    except Exception as exc:
        db.delete(sent_row)
        db.flush()
        sender.next_ready_at = _next_sender_ready_at(now)
        lead.delivery_state = "queued"
        lead.lock_token = None
        lead.locked_at = None
        lead.next_eligible_at = now + timedelta(hours=1)
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

    sent_row.event_metadata = {"message_id": message_id}
    sender.sent_count_today = int(sender.sent_count_today or 0) + 1
    sender.last_used_at = now
    sender.next_ready_at = _next_sender_ready_at(now)

    next_step = _resolve_followup_step(current_step, db)
    if next_step:
        lead.next_step_id = next_step.step_id
        lead.next_eligible_at = _next_step_schedule_utc(lead.campaign, next_step, now)
        lead.delivery_state = "queued"
    else:
        lead.next_step_id = None
        lead.next_eligible_at = None
        lead.delivery_state = "completed"

    lead.lock_token = None
    lead.locked_at = None
    db.commit()


def run_warmup_iteration(db: Session) -> int:
    warmup_pool = load_global_warmup_pool(db)
    peer_emails_lower = global_warmup_peer_emails_lower(warmup_pool)
    order = list(warmup_pool)
    random.shuffle(order)

    sent = 0
    now = datetime.now(timezone.utc)
    n = len(order)
    if n < 2:
        db.commit()
        return sent

    for i, sender in enumerate(order):
        recipient = order[(i + 1) % n]
        if (sender.email or "").lower() == (recipient.email or "").lower():
            continue
        if sender.sent_count_today >= _effective_daily_limit(sender):
            continue
        time.sleep(random.uniform(5.0, 15.0))
        _imap_rescue_warmup_spam_to_inbox(recipient, peer_emails_lower)
        subject, html_body, plain_body = _pick_warmup_message()
        thread_id = str(uuid.uuid4())
        try:
            message_id = _send_smtp(
                account=sender,
                recipient=recipient.email,
                subject=subject,
                html_body=html_body,
                plain_body=plain_body,
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
        _imap_rescue_warmup_spam_to_inbox(recipient, peer_emails_lower)
    db.commit()
    return sent


def run_imap_reply_iteration(db: Session) -> int:
    """
    Warmup-only IMAP pass: move mis-filed warmup mail from Spam/Junk back to INBOX.

    Lead reply detection and Unibox persistence live exclusively in
    ``ingestion_service`` (header prefetch + RFC822 for matching leads). A second
    inbox scan here previously duplicated reply ``EmailEvent`` rows without
    always inserting ``UniboxMessage`` rows (stale ORM ``last_imap_uid`` on the
    API session after parallel ingest, and lighter FROM-only parsing).
    """
    warmup_pool = load_global_warmup_pool(db)
    warmup_peer_emails_lower = global_warmup_peer_emails_lower(warmup_pool)
    accounts = (
        db.query(SenderAccount)
        .options(joinedload(SenderAccount.warmup_settings))
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
            with imaplib.IMAP4_SSL(
                account.imap_host, int(account.imap_port), timeout=IMAP_SOCKET_TIMEOUT
            ) as client:
                client.login(account.email, account.app_password)
                if account.warmup_settings and account.warmup_settings.is_warmup_active:
                    _imap_rescue_warmup_spam_on_client(client, account, warmup_peer_emails_lower)
            db.commit()
        except Exception:
            db.rollback()
            continue
    return 0

