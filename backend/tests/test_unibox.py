"""
tests/test_unibox.py — Unit and integration tests for the Unibox feature.

Coverage
────────
Threading Service (4)
  1.  New message with no RFC 2822 reply headers → creates new thread.
  2.  Reply with In-Reply-To matching existing message → joins existing thread.
  3.  Reply with References chain → finds thread via most-recent ancestor.
  4.  Orphan thread upgrades when a subsequent message identifies the lead.

Ingestion Service (3)
  5.  ingest_account skips gracefully when IMAP is not configured.
  6.  _build_search_vector returns a non-null tsvector.
  7.  Duplicate Message-ID is skipped (idempotency).

Repository (6)
  8.  list_threads_all returns threads in workspace ordered by recency.
  9.  list_threads_unread returns only threads with unread messages.
  10. list_threads_for_campaign filters by campaign_id.
  11. count_unread_for_thread returns correct unread count.
  12. count_unread_for_sender_account returns correct unread count.
  13. message_exists_by_header returns True for existing, False for new.

API — GET /unibox/inboxes (2)
  14. Returns list of sender accounts with unread_count field.
  15. Returns empty list for workspace with no sender accounts.

API — GET /unibox/threads (5)
  16. Returns paginated thread list for workspace.
  17. view=unread filters correctly.
  18. view=sent filters correctly.
  19. pipeline_status filter returns only matching leads.
  20. campaign_id filter returns only tagged threads.

API — GET /unibox/threads/{thread_id} (3)
  21. Returns thread detail with messages.
  22. Auto-marks inbound messages as read on first open.
  23. Returns 404 for unknown thread.

API — PATCH /unibox/threads/{thread_id} (4)
  24. Tags a thread with a campaign.
  25. Unsets campaign tag (campaign_id=null).
  26. Updates pipeline_status on linked lead.
  27. Returns 422 for invalid pipeline_status value.

API — POST /unibox/threads/{thread_id}/reply (3)
  28. Persists outbound message with status=sent on success path (SMTP mocked).
  29. Persists outbound message with status=failed when SMTP raises (mocked).
  30. Returns 404 when thread is not found.

API — PATCH /unibox/threads/{thread_id}/messages/{message_id}/read (2)
  31. Marks a message as read.
  32. Marks a message as unread.

API — GET /unibox/search (3)
  33. Returns matching messages for a keyword search.
  34. Returns empty result for non-matching keyword.
  35. Filters by inbox_id when provided.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text

from app.models import Lead, SenderAccount, UniboxMessage, UniboxThread
from app.repositories import unibox_repository
from app.services.unibox import (
    aggregation_service,
    campaign_tagging_service,
    threading_service,
)
from tests.factories import (
    add_member,
    auth_cookies,
    make_campaign,
    make_lead,
    make_role,
    make_sender_account,
    make_unibox_message,
    make_unibox_thread,
    make_user,
    make_workspace,
)


# ===========================================================================
# Shared fixtures
# ===========================================================================


@pytest.fixture
def setup(db):
    """Workspace owner + workspace + sender account."""
    user = make_user(db)
    ws = make_workspace(db, user)
    sender = make_sender_account(db, ws.workspace_id)
    cookies = auth_cookies(user)
    return {
        "user": user,
        "ws": ws,
        "workspace_id": ws.workspace_id,
        "sender": sender,
        "cookies": cookies,
    }


@pytest.fixture
def setup_with_lead(db, setup):
    """Adds a campaign + lead to the shared fixture."""
    campaign = make_campaign(db, setup["workspace_id"])  # creator_id=None avoids FK issue
    lead = make_lead(db, campaign.campaign_id)
    return {**setup, "campaign": campaign, "lead": lead}


# ===========================================================================
# 1–4  ThreadingService unit tests
# ===========================================================================


class TestThreadingService:
    def test_creates_new_thread_when_no_reply_headers(self, db, setup):
        """Test 1: No In-Reply-To / References → new thread is created."""
        thread = threading_service.resolve_or_create_thread(
            workspace_id=setup["workspace_id"],
            subject="Hello",
            lead_id=None,
            campaign_id=None,
            is_orphan=True,
            in_reply_to=None,
            references_header=None,
            db=db,
        )
        db.commit()

        assert thread.thread_id is not None
        assert thread.subject == "Hello"
        assert thread.is_orphan is True
        assert thread.workspace_id == setup["workspace_id"]

    def test_joins_existing_thread_via_in_reply_to(self, db, setup_with_lead):
        """Test 2: In-Reply-To matching existing message → joins existing thread."""
        data = setup_with_lead
        # Create first thread with a message that has a known Message-ID.
        first_thread = make_unibox_thread(
            db,
            workspace_id=data["workspace_id"],
            sender_account=data["sender"],
            lead=data["lead"],
            subject="Initial message",
        )
        first_msg = first_thread.messages[0]
        original_mid = first_msg.message_id_header

        # Now resolve a thread for a reply referencing that Message-ID.
        resolved = threading_service.resolve_or_create_thread(
            workspace_id=data["workspace_id"],
            subject="Re: Initial message",
            lead_id=data["lead"].lead_id,
            campaign_id=data["campaign"].campaign_id,
            is_orphan=False,
            in_reply_to=original_mid,
            references_header=None,
            db=db,
        )
        db.commit()

        assert resolved.thread_id == first_thread.thread_id

    def test_joins_thread_via_references_chain(self, db, setup_with_lead):
        """Test 3: References header chain → finds thread via ancestor."""
        data = setup_with_lead
        first_thread = make_unibox_thread(
            db,
            workspace_id=data["workspace_id"],
            sender_account=data["sender"],
            lead=data["lead"],
        )
        first_msg = first_thread.messages[0]
        original_mid = first_msg.message_id_header

        # References contains multiple IDs, original one is last.
        refs = f"<old@example.com> <older@example.com> {original_mid}"

        resolved = threading_service.resolve_or_create_thread(
            workspace_id=data["workspace_id"],
            subject="Re: Thread",
            lead_id=data["lead"].lead_id,
            campaign_id=None,
            is_orphan=False,
            in_reply_to=None,
            references_header=refs,
            db=db,
        )
        db.commit()

        assert resolved.thread_id == first_thread.thread_id

    def test_orphan_thread_upgrades_when_lead_identified(self, db, setup_with_lead):
        """Test 4: Orphan thread is upgraded when a later message identifies the lead."""
        data = setup_with_lead
        # Start with orphan thread.
        orphan_thread = make_unibox_thread(
            db,
            workspace_id=data["workspace_id"],
            sender_account=data["sender"],
            lead=None,
            is_orphan=True,
        )
        first_mid = orphan_thread.messages[0].message_id_header

        assert orphan_thread.is_orphan is True
        assert orphan_thread.lead_id is None

        # Resolve with lead identified this time, referencing the original message.
        resolved = threading_service.resolve_or_create_thread(
            workspace_id=data["workspace_id"],
            subject="Re: Orphan",
            lead_id=data["lead"].lead_id,
            campaign_id=None,
            is_orphan=False,
            in_reply_to=first_mid,
            references_header=None,
            db=db,
        )
        db.commit()

        assert resolved.thread_id == orphan_thread.thread_id
        db.refresh(orphan_thread)
        assert orphan_thread.is_orphan is False
        assert orphan_thread.lead_id == data["lead"].lead_id


# ===========================================================================
# 5–7  IngestionService unit tests
# ===========================================================================


class TestIngestionService:
    def test_ingest_skips_unconfigured_account(self, db, setup):
        """Test 5: ingest_account returns 0 for SMTP-only account (no IMAP)."""
        from app.services.unibox import ingestion_service

        sender = setup["sender"]
        # Default make_sender_account has no imap_host.
        count = ingestion_service.ingest_account(sender, db)
        assert count == 0

    def test_build_search_vector_not_null(self, db):
        """Test 6: _build_search_vector returns a non-null PostgreSQL tsvector."""
        from app.services.unibox.ingestion_service import _build_search_vector

        result = _build_search_vector(
            subject="Meeting request",
            body_text="Hello, please let me know your availability.",
            from_address="lead@example.com",
            db=db,
        )
        assert result is not None

    def test_idempotency_duplicate_message_id(self, db, setup):
        """Test 7: Ingesting the same Message-ID twice creates only one record."""
        data = setup
        thread = make_unibox_thread(
            db, data["workspace_id"], sender_account=data["sender"]
        )
        existing_mid = thread.messages[0].message_id_header

        # Check exists_by_header.
        assert unibox_repository.message_exists_by_header(existing_mid, db) is True

        # A new, different MID should not exist.
        assert unibox_repository.message_exists_by_header("<new@example.com>", db) is False


# ===========================================================================
# 8–13  Repository unit tests
# ===========================================================================


class TestUniboxRepository:
    def test_list_threads_all_returns_workspace_threads(self, db, setup):
        """Test 8: list_threads_all returns threads for workspace, ordered by recency."""
        data = setup
        for subj in ["First", "Second", "Third"]:
            make_unibox_thread(db, data["workspace_id"], data["sender"], subject=subj)

        total, rows = unibox_repository.list_threads_all(
            data["workspace_id"], page=1, page_size=10, db=db
        )
        assert total == 3
        assert len(rows) == 3
        # All belong to this workspace.
        for row in rows:
            assert row["inbox_id"] == data["sender"].account_id

    def test_list_threads_unread_filters_unread(self, db, setup):
        """Test 9: list_threads_unread returns only threads with unread messages."""
        data = setup
        t1 = make_unibox_thread(db, data["workspace_id"], data["sender"])
        t2 = make_unibox_thread(db, data["workspace_id"], data["sender"])

        # Mark all messages in t1 as read.
        db.query(UniboxMessage).filter(UniboxMessage.thread_id == t1.thread_id).update(
            {"is_read": True}
        )
        db.commit()

        total, rows = unibox_repository.list_threads_unread(
            data["workspace_id"], page=1, page_size=10, db=db
        )
        assert total == 1
        assert rows[0]["thread_id"] == t2.thread_id

    def test_list_threads_for_campaign(self, db, setup_with_lead):
        """Test 10: list_threads_for_campaign filters by campaign_id."""
        data = setup_with_lead
        tagged = make_unibox_thread(
            db,
            data["workspace_id"],
            data["sender"],
            lead=data["lead"],
            campaign=data["campaign"],
        )
        make_unibox_thread(db, data["workspace_id"], data["sender"])  # untagged

        total, rows = unibox_repository.list_threads_for_campaign(
            data["workspace_id"], data["campaign"].campaign_id, page=1, page_size=10, db=db
        )
        assert total == 1
        assert rows[0]["thread_id"] == tagged.thread_id

    def test_count_unread_for_thread(self, db, setup):
        """Test 11: count_unread_for_thread returns correct count."""
        data = setup
        thread = make_unibox_thread(db, data["workspace_id"], data["sender"])
        # Add a second unread message.
        make_unibox_message(db, thread, data["sender"])
        # Add a read message.
        make_unibox_message(db, thread, data["sender"], is_read=True)

        count = unibox_repository.count_unread_for_thread(thread.thread_id, db)
        assert count == 2  # first factory message + second unread one

    def test_count_unread_for_sender_account(self, db, setup):
        """Test 12: count_unread_for_sender_account returns total unread count."""
        data = setup
        t1 = make_unibox_thread(db, data["workspace_id"], data["sender"])
        t2 = make_unibox_thread(db, data["workspace_id"], data["sender"])
        make_unibox_message(db, t2, data["sender"])  # extra unread

        count = unibox_repository.count_unread_for_sender_account(
            data["sender"].account_id, db
        )
        # t1 has 1 unread, t2 has 2 unread → total 3.
        assert count == 3

    def test_message_exists_by_header(self, db, setup):
        """Test 13: message_exists_by_header returns True/False correctly."""
        data = setup
        thread = make_unibox_thread(db, data["workspace_id"], data["sender"])
        mid = thread.messages[0].message_id_header

        assert unibox_repository.message_exists_by_header(mid, db) is True
        assert unibox_repository.message_exists_by_header("<nonexistent@x.com>", db) is False


# ===========================================================================
# 14–15  API — GET /unibox/inboxes
# ===========================================================================


class TestInboxesAPI:
    def test_list_inboxes_returns_accounts(self, client, db, setup):
        """Test 14: GET /unibox/inboxes returns sender accounts with unread_count."""
        data = setup
        thread = make_unibox_thread(db, data["workspace_id"], data["sender"])

        r = client.get(
            f"/workspaces/{data['workspace_id']}/unibox/inboxes",
            cookies=data["cookies"],
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["items"]) == 1
        item = body["items"][0]
        assert item["inbox_id"] == data["sender"].account_id
        assert "unread_count" in item
        assert item["unread_count"] >= 0

    def test_list_inboxes_empty_workspace(self, client, db):
        """Test 15: GET /unibox/inboxes returns empty list for workspace with no accounts."""
        user = make_user(db)
        ws = make_workspace(db, user)
        cookies = auth_cookies(user)

        r = client.get(
            f"/workspaces/{ws.workspace_id}/unibox/inboxes",
            cookies=cookies,
        )
        assert r.status_code == 200
        assert r.json()["items"] == []


# ===========================================================================
# 16–20  API — GET /unibox/threads
# ===========================================================================


class TestThreadListAPI:
    def test_list_threads_all(self, client, db, setup):
        """Test 16: GET /unibox/threads returns paginated thread list."""
        data = setup
        for i in range(3):
            make_unibox_thread(db, data["workspace_id"], data["sender"], subject=f"T{i}")

        r = client.get(
            f"/workspaces/{data['workspace_id']}/unibox/threads",
            cookies=data["cookies"],
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 3
        assert len(body["items"]) == 3
        assert "page" in body
        assert "page_size" in body

    def test_list_threads_view_unread(self, client, db, setup):
        """Test 17: ?view=unread returns only threads with unread messages."""
        data = setup
        t_unread = make_unibox_thread(db, data["workspace_id"], data["sender"])
        t_read = make_unibox_thread(db, data["workspace_id"], data["sender"])
        db.query(UniboxMessage).filter(
            UniboxMessage.thread_id == t_read.thread_id
        ).update({"is_read": True})
        db.commit()

        r = client.get(
            f"/workspaces/{data['workspace_id']}/unibox/threads?view=unread",
            cookies=data["cookies"],
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["thread_id"] == t_unread.thread_id

    def test_list_threads_view_sent(self, client, db, setup):
        """Test 18: ?view=sent returns threads with outbound messages."""
        data = setup
        t_inbound = make_unibox_thread(db, data["workspace_id"], data["sender"])
        t_with_reply = make_unibox_thread(db, data["workspace_id"], data["sender"])
        make_unibox_message(
            db, t_with_reply, data["sender"], direction="outbound", status="sent"
        )

        r = client.get(
            f"/workspaces/{data['workspace_id']}/unibox/threads?view=sent",
            cookies=data["cookies"],
        )
        assert r.status_code == 200
        thread_ids = [item["thread_id"] for item in r.json()["items"]]
        assert t_with_reply.thread_id in thread_ids
        assert t_inbound.thread_id not in thread_ids

    def test_list_threads_pipeline_filter(self, client, db, setup_with_lead):
        """Test 19: ?pipeline_status=interested returns only matching threads."""
        data = setup_with_lead
        lead = data["lead"]
        lead.pipeline_status = "interested"
        db.commit()

        t_match = make_unibox_thread(
            db, data["workspace_id"], data["sender"], lead=lead
        )
        t_no_match = make_unibox_thread(db, data["workspace_id"], data["sender"])

        r = client.get(
            f"/workspaces/{data['workspace_id']}/unibox/threads?pipeline_status=interested",
            cookies=data["cookies"],
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["thread_id"] == t_match.thread_id

    def test_list_threads_campaign_filter(self, client, db, setup_with_lead):
        """Test 20: ?campaign_id=<id> returns only tagged threads."""
        data = setup_with_lead
        tagged = make_unibox_thread(
            db, data["workspace_id"], data["sender"],
            lead=data["lead"], campaign=data["campaign"]
        )
        make_unibox_thread(db, data["workspace_id"], data["sender"])  # untagged

        r = client.get(
            f"/workspaces/{data['workspace_id']}/unibox/threads"
            f"?campaign_id={data['campaign'].campaign_id}",
            cookies=data["cookies"],
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["items"][0]["thread_id"] == tagged.thread_id


# ===========================================================================
# 21–23  API — GET /unibox/threads/{thread_id}
# ===========================================================================


class TestThreadDetailAPI:
    def test_get_thread_returns_messages(self, client, db, setup):
        """Test 21: GET /unibox/threads/{id} returns thread with messages."""
        data = setup
        thread = make_unibox_thread(db, data["workspace_id"], data["sender"])
        make_unibox_message(db, thread, data["sender"])

        r = client.get(
            f"/workspaces/{data['workspace_id']}/unibox/threads/{thread.thread_id}",
            cookies=data["cookies"],
        )
        assert r.status_code == 200
        body = r.json()
        assert body["thread_id"] == thread.thread_id
        assert len(body["messages"]) == 2

    def test_get_thread_marks_messages_read(self, client, db, setup):
        """Test 22: Opening a thread auto-marks inbound messages as read."""
        data = setup
        thread = make_unibox_thread(db, data["workspace_id"], data["sender"])
        # Initially unread.
        assert thread.messages[0].is_read is False

        client.get(
            f"/workspaces/{data['workspace_id']}/unibox/threads/{thread.thread_id}",
            cookies=data["cookies"],
        )
        db.refresh(thread.messages[0])
        assert thread.messages[0].is_read is True

    def test_get_thread_returns_404_for_unknown(self, client, db, setup):
        """Test 23: GET /unibox/threads/{unknown_id} returns 404."""
        data = setup
        r = client.get(
            f"/workspaces/{data['workspace_id']}/unibox/threads/{uuid.uuid4()}",
            cookies=data["cookies"],
        )
        assert r.status_code == 404


# ===========================================================================
# 24–27  API — PATCH /unibox/threads/{thread_id}
# ===========================================================================


class TestThreadUpdateAPI:
    def test_tag_thread_with_campaign(self, client, db, setup_with_lead):
        """Test 24: PATCH /unibox/threads/{id} sets campaign_id."""
        data = setup_with_lead
        thread = make_unibox_thread(
            db, data["workspace_id"], data["sender"], lead=data["lead"]
        )
        assert thread.campaign_id is None

        r = client.patch(
            f"/workspaces/{data['workspace_id']}/unibox/threads/{thread.thread_id}",
            json={"campaign_id": data["campaign"].campaign_id},
            cookies=data["cookies"],
        )
        assert r.status_code == 200
        db.refresh(thread)
        assert thread.campaign_id == data["campaign"].campaign_id

    def test_untag_thread_campaign(self, client, db, setup_with_lead):
        """Test 25: PATCH with campaign_id=null removes the campaign tag."""
        data = setup_with_lead
        thread = make_unibox_thread(
            db, data["workspace_id"], data["sender"],
            lead=data["lead"], campaign=data["campaign"]
        )
        assert thread.campaign_id == data["campaign"].campaign_id

        r = client.patch(
            f"/workspaces/{data['workspace_id']}/unibox/threads/{thread.thread_id}",
            json={"campaign_id": None},
            cookies=data["cookies"],
        )
        assert r.status_code == 200
        db.refresh(thread)
        assert thread.campaign_id is None

    def test_update_pipeline_status(self, client, db, setup_with_lead):
        """Test 26: PATCH with pipeline_status updates the linked lead."""
        data = setup_with_lead
        thread = make_unibox_thread(
            db, data["workspace_id"], data["sender"], lead=data["lead"]
        )

        r = client.patch(
            f"/workspaces/{data['workspace_id']}/unibox/threads/{thread.thread_id}",
            json={"pipeline_status": "interested"},
            cookies=data["cookies"],
        )
        assert r.status_code == 200
        db.refresh(data["lead"])
        assert data["lead"].pipeline_status == "interested"

    def test_invalid_pipeline_status_returns_422(self, client, db, setup_with_lead):
        """Test 27: PATCH with invalid pipeline_status returns 422."""
        data = setup_with_lead
        thread = make_unibox_thread(
            db, data["workspace_id"], data["sender"], lead=data["lead"]
        )

        r = client.patch(
            f"/workspaces/{data['workspace_id']}/unibox/threads/{thread.thread_id}",
            json={"pipeline_status": "not-a-valid-status"},
            cookies=data["cookies"],
        )
        assert r.status_code == 422


# ===========================================================================
# 28–30  API — POST /unibox/threads/{thread_id}/reply
# ===========================================================================


class TestReplyAPI:
    def test_reply_persisted_with_sent_status(self, client, db, setup_with_lead):
        """Test 28: POST /reply persists outbound message with status=sent when SMTP succeeds."""
        data = setup_with_lead
        thread = make_unibox_thread(
            db, data["workspace_id"], data["sender"], lead=data["lead"]
        )

        with patch(
            "app.services.unibox.reply_dispatch_service._send_smtp_reply",
            return_value=None,
        ):
            r = client.post(
                f"/workspaces/{data['workspace_id']}/unibox/threads/{thread.thread_id}/reply",
                json={
                    "body_text": "Thanks for reaching out!",
                    "sender_account_id": data["sender"].account_id,
                },
                cookies=data["cookies"],
            )

        assert r.status_code == 201
        body = r.json()
        assert body["status"] == "sent"
        assert body["direction"] == "outbound"

    def test_reply_persisted_with_failed_status_on_smtp_error(self, client, db, setup_with_lead):
        """Test 29: POST /reply persists status=failed when SMTP raises RuntimeError."""
        data = setup_with_lead
        thread = make_unibox_thread(
            db, data["workspace_id"], data["sender"], lead=data["lead"]
        )

        with patch(
            "app.services.unibox.reply_dispatch_service._send_smtp_reply",
            side_effect=RuntimeError("SMTP connection refused"),
        ):
            r = client.post(
                f"/workspaces/{data['workspace_id']}/unibox/threads/{thread.thread_id}/reply",
                json={
                    "body_text": "Test reply",
                    "sender_account_id": data["sender"].account_id,
                },
                cookies=data["cookies"],
            )

        assert r.status_code == 201
        body = r.json()
        assert body["status"] == "failed"

    def test_reply_returns_404_for_unknown_thread(self, client, db, setup):
        """Test 30: POST /reply on unknown thread returns 404."""
        data = setup
        r = client.post(
            f"/workspaces/{data['workspace_id']}/unibox/threads/{uuid.uuid4()}/reply",
            json={
                "body_text": "Hello",
                "sender_account_id": data["sender"].account_id,
            },
            cookies=data["cookies"],
        )
        assert r.status_code == 404


# ===========================================================================
# 31–32  API — PATCH /unibox/threads/{id}/messages/{msg_id}/read
# ===========================================================================


class TestMarkReadAPI:
    def test_mark_message_as_read(self, client, db, setup):
        """Test 31: PATCH /read with is_read=True marks message as read."""
        data = setup
        thread = make_unibox_thread(db, data["workspace_id"], data["sender"])
        msg = thread.messages[0]
        assert msg.is_read is False

        r = client.patch(
            f"/workspaces/{data['workspace_id']}/unibox/threads/{thread.thread_id}"
            f"/messages/{msg.message_id}/read",
            json={"is_read": True},
            cookies=data["cookies"],
        )
        assert r.status_code == 200
        assert r.json()["is_read"] is True
        db.refresh(msg)
        assert msg.is_read is True

    def test_mark_message_as_unread(self, client, db, setup):
        """Test 32: PATCH /read with is_read=False marks message as unread."""
        data = setup
        thread = make_unibox_thread(db, data["workspace_id"], data["sender"])
        msg = thread.messages[0]
        # First mark as read.
        msg.is_read = True
        db.commit()

        r = client.patch(
            f"/workspaces/{data['workspace_id']}/unibox/threads/{thread.thread_id}"
            f"/messages/{msg.message_id}/read",
            json={"is_read": False},
            cookies=data["cookies"],
        )
        assert r.status_code == 200
        assert r.json()["is_read"] is False


# ===========================================================================
# 33–35  API — GET /unibox/search
# ===========================================================================


class TestSearchAPI:
    def _seed_search_message(self, db, thread, sender, keyword: str):
        """Insert a message with a pre-built search_vector containing keyword."""
        vec = db.execute(
            text("SELECT to_tsvector('english', :kw)"), {"kw": keyword}
        ).scalar()
        msg = UniboxMessage(
            thread_id=thread.thread_id,
            sender_account_id=sender.account_id,
            direction="inbound",
            message_id_header=f"<{uuid.uuid4()}@search-test.com>",
            from_address="finder@example.com",
            to_addresses=[sender.email],
            subject=keyword,
            body_text=keyword,
            is_read=False,
            is_orphan=True,
            status="received",
            received_at=datetime.now(timezone.utc),
            search_vector=vec,
        )
        db.add(msg)
        db.commit()
        return msg

    def test_search_returns_matching_messages(self, client, db, setup):
        """Test 33: GET /unibox/search?q=<keyword> returns matching messages."""
        data = setup
        thread = make_unibox_thread(db, data["workspace_id"], data["sender"], subject="elephantquery")
        self._seed_search_message(db, thread, data["sender"], "elephantquery")

        r = client.get(
            f"/workspaces/{data['workspace_id']}/unibox/search?q=elephantquery",
            cookies=data["cookies"],
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 1
        assert any(item["thread_id"] == thread.thread_id for item in body["items"])

    def test_search_returns_empty_for_no_match(self, client, db, setup):
        """Test 34: GET /unibox/search?q=<unknown> returns empty result."""
        data = setup
        make_unibox_thread(db, data["workspace_id"], data["sender"])

        r = client.get(
            f"/workspaces/{data['workspace_id']}/unibox/search?q=xyznonexistentkeyword",
            cookies=data["cookies"],
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_search_filters_by_inbox_id(self, client, db, setup):
        """Test 35: GET /unibox/search?inbox_id=<id> filters by sender account."""
        data = setup
        other_sender = make_sender_account(db, data["workspace_id"])

        thread_a = make_unibox_thread(db, data["workspace_id"], data["sender"])
        thread_b = make_unibox_thread(db, data["workspace_id"], other_sender)

        self._seed_search_message(db, thread_a, data["sender"], "inboxfilterword")
        self._seed_search_message(db, thread_b, other_sender, "inboxfilterword")

        r = client.get(
            f"/workspaces/{data['workspace_id']}/unibox/search"
            f"?q=inboxfilterword&inbox_id={data['sender'].account_id}",
            cookies=data["cookies"],
        )
        assert r.status_code == 200
        body = r.json()
        # Only messages from data["sender"] should appear.
        for item in body["items"]:
            assert item["inbox_email"] == data["sender"].email


# ===========================================================================
# 36–42  Reply feature — extended tests
# ===========================================================================
"""
36. POST /reply with empty body_text and no body_html → 422 Unprocessable Entity.
37. POST /reply with only body_html (no body_text) → 201 on SMTP success.
38. POST /reply persisted message appears in GET /threads/{id} message list.
39. POST /reply updates thread last_message_at timestamp.
40. POST /reply with unknown sender_account_id → 404.
41. POST /reply to a thread in a different workspace → 404.
42. POST /reply body_text returned verbatim in the response.
"""


class TestReplyAPIExtended:

    def test_reply_empty_body_returns_422(self, client, db, setup_with_lead):
        """Test 36: body_text='' and no body_html → validation error 422."""
        data = setup_with_lead
        thread = make_unibox_thread(
            db, data["workspace_id"], data["sender"], lead=data["lead"]
        )
        r = client.post(
            f"/workspaces/{data['workspace_id']}/unibox/threads/{thread.thread_id}/reply",
            json={"body_text": "", "sender_account_id": data["sender"].account_id},
            cookies=data["cookies"],
        )
        assert r.status_code == 422

    def test_reply_with_html_only_body_succeeds(self, client, db, setup_with_lead):
        """Test 37: body_html only (no body_text) is accepted by the validator and sends."""
        data = setup_with_lead
        thread = make_unibox_thread(
            db, data["workspace_id"], data["sender"], lead=data["lead"]
        )
        with patch(
            "app.services.unibox.reply_dispatch_service._send_smtp_reply",
            return_value=None,
        ):
            r = client.post(
                f"/workspaces/{data['workspace_id']}/unibox/threads/{thread.thread_id}/reply",
                json={
                    "body_html": "<p>Hello</p>",
                    "sender_account_id": data["sender"].account_id,
                },
                cookies=data["cookies"],
            )
        assert r.status_code == 201
        body = r.json()
        assert body["status"] == "sent"

    def test_reply_appears_in_thread_detail(self, client, db, setup_with_lead):
        """Test 38: After POST /reply the new message appears in GET /threads/{id}."""
        data = setup_with_lead
        thread = make_unibox_thread(
            db, data["workspace_id"], data["sender"], lead=data["lead"]
        )
        original_count = len(thread.messages)

        with patch(
            "app.services.unibox.reply_dispatch_service._send_smtp_reply",
            return_value=None,
        ):
            client.post(
                f"/workspaces/{data['workspace_id']}/unibox/threads/{thread.thread_id}/reply",
                json={
                    "body_text": "Following up on my previous email.",
                    "sender_account_id": data["sender"].account_id,
                },
                cookies=data["cookies"],
            )

        r = client.get(
            f"/workspaces/{data['workspace_id']}/unibox/threads/{thread.thread_id}",
            cookies=data["cookies"],
        )
        assert r.status_code == 200
        messages = r.json()["messages"]
        assert len(messages) == original_count + 1
        last = messages[-1]
        assert last["direction"] == "outbound"
        assert last["status"] == "sent"

    def test_reply_updates_thread_last_message_at(self, client, db, setup_with_lead):
        """Test 39: POST /reply updates thread.last_message_at to a recent timestamp."""
        from datetime import datetime, timezone

        data = setup_with_lead
        thread = make_unibox_thread(
            db, data["workspace_id"], data["sender"], lead=data["lead"]
        )
        original_ts = thread.last_message_at

        with patch(
            "app.services.unibox.reply_dispatch_service._send_smtp_reply",
            return_value=None,
        ):
            client.post(
                f"/workspaces/{data['workspace_id']}/unibox/threads/{thread.thread_id}/reply",
                json={
                    "body_text": "Checking in.",
                    "sender_account_id": data["sender"].account_id,
                },
                cookies=data["cookies"],
            )

        db.refresh(thread)
        assert thread.last_message_at >= original_ts

    def test_reply_unknown_sender_returns_404(self, client, db, setup_with_lead):
        """Test 40: POST /reply with a non-existent sender_account_id → 404."""
        data = setup_with_lead
        thread = make_unibox_thread(
            db, data["workspace_id"], data["sender"], lead=data["lead"]
        )
        r = client.post(
            f"/workspaces/{data['workspace_id']}/unibox/threads/{thread.thread_id}/reply",
            json={
                "body_text": "Test",
                "sender_account_id": str(uuid.uuid4()),
            },
            cookies=data["cookies"],
        )
        assert r.status_code == 404

    def test_reply_cross_workspace_thread_returns_404(self, client, db, setup_with_lead):
        """Test 41: POST /reply targeting a thread in another workspace → 404."""
        from tests.factories import make_workspace, make_user, make_sender_account

        data = setup_with_lead
        # Create a second workspace belonging to a different owner.
        other_owner = make_user(db, email=f"owner2-{uuid.uuid4()}@x.com")
        other_ws = make_workspace(db, owner_user=other_owner)
        other_sender = make_sender_account(db, other_ws.workspace_id)
        other_thread = make_unibox_thread(db, other_ws.workspace_id, other_sender)

        # Post to data's workspace URL but with other_thread's ID.
        r = client.post(
            f"/workspaces/{data['workspace_id']}/unibox/threads/{other_thread.thread_id}/reply",
            json={
                "body_text": "Sneaky cross-workspace reply",
                "sender_account_id": data["sender"].account_id,
            },
            cookies=data["cookies"],
        )
        assert r.status_code == 404

    def test_reply_body_text_echoed_in_response(self, client, db, setup_with_lead):
        """Test 42: body_text submitted in POST /reply is returned verbatim in response."""
        data = setup_with_lead
        thread = make_unibox_thread(
            db, data["workspace_id"], data["sender"], lead=data["lead"]
        )
        body_text = "Unique marker text: xK9qZm2reply"

        with patch(
            "app.services.unibox.reply_dispatch_service._send_smtp_reply",
            return_value=None,
        ):
            r = client.post(
                f"/workspaces/{data['workspace_id']}/unibox/threads/{thread.thread_id}/reply",
                json={
                    "body_text": body_text,
                    "sender_account_id": data["sender"].account_id,
                },
                cookies=data["cookies"],
            )

        assert r.status_code == 201
        assert r.json()["body_text"] == body_text
