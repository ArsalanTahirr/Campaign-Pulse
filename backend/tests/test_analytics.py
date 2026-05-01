"""
tests/test_analytics.py — Unit and integration tests for the analytics dashboard.

Coverage
────────
Calculation Tests (7)
  1.  open_rate  = 0 when total_delivered = 0  (no ZeroDivisionError)
  2.  click_rate = 0 when total_delivered = 0
  3.  reply_rate = 0 when total_delivered = 0
  4.  replied.rate rounds to 2 decimal places
  5.  Uniqueness — 5 open events for same lead → unique_opens = 1
  6.  Unique clicks — same lead clicks 10 times in one campaign → 1 unique click
  7.  sequence_started counts only leads with a step-1 sent event, not enrolled leads

Edge Case Tests (4)
  8.  Campaign with zero replies → replied: {count: 0, rate: 0.00}
  9.  Account performance with no sends → all fields 0, never null
  10. Graph endpoint with no data in range → empty values: [], no error
  11. tracking_enabled is present and is True

API Tests (3)
  12. Graph returns exactly 4 series with correct keys in order
  13. Campaign status field only ever returns 'active' or 'completed'
  14. Account performance is scoped to the requested campaign_id
"""

import pytest

from tests.factories import (
    add_member,
    attach_sender_to_campaign,
    auth_cookies,
    make_campaign,
    make_email_event,
    make_lead,
    make_role,
    make_sender_account,
    make_step,
    make_user,
    make_workspace,
)


# ===========================================================================
# Shared fixture: authenticated workspace owner + workspace
# ===========================================================================


@pytest.fixture
def setup(db):
    """
    Returns a dict with:
        user, workspace, cookies, workspace_id
    The user is the Owner of the workspace.
    """
    user = make_user(db)
    ws = make_workspace(db, user)
    cookies = auth_cookies(user)
    return {"user": user, "workspace": ws, "cookies": cookies, "workspace_id": ws.workspace_id}


# ===========================================================================
# Calculation Tests
# ===========================================================================


def test_open_rate_zero_when_no_delivered(client, db, setup):
    """open_rate must be 0.0 when total_delivered = 0 — no ZeroDivisionError."""
    ws_id = setup["workspace_id"]
    resp = client.get(f"/workspaces/{ws_id}/analytics/summary", cookies=setup["cookies"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sent"] == 0
    assert data["open_rate"] == 0.0


def test_click_rate_zero_when_no_delivered(client, db, setup):
    """click_rate must be 0.0 when total_delivered = 0 — no ZeroDivisionError."""
    ws_id = setup["workspace_id"]
    resp = client.get(f"/workspaces/{ws_id}/analytics/summary", cookies=setup["cookies"])
    assert resp.status_code == 200
    assert resp.json()["click_rate"] == 0.0


def test_reply_rate_zero_when_no_delivered(client, db, setup):
    """reply_rate must be 0.0 when total_delivered = 0 — no ZeroDivisionError."""
    ws_id = setup["workspace_id"]
    resp = client.get(f"/workspaces/{ws_id}/analytics/summary", cookies=setup["cookies"])
    assert resp.status_code == 200
    assert resp.json()["reply_rate"] == 0.0


def test_replied_rate_rounds_to_2_decimal_places(client, db, setup):
    """
    replied.rate must round to exactly 2 decimal places.
    2 replied out of 14 sequence_started = 14.285714... → should be 14.29.
    """
    ws_id = setup["workspace_id"]
    campaign = make_campaign(db, ws_id, status="active")
    step1 = make_step(db, campaign.campaign_id, step_number=1)
    sender = make_sender_account(db, ws_id)

    # Create 14 leads, all receiving step-1 sent events.
    leads = [make_lead(db, campaign.campaign_id) for _ in range(14)]
    for lead in leads:
        make_email_event(db, lead.lead_id, "sent", sender.account_id, step1.step_id)

    # Only 2 of those 14 leads reply.
    make_email_event(db, leads[0].lead_id, "replied", sender.account_id)
    make_email_event(db, leads[1].lead_id, "replied", sender.account_id)

    resp = client.get(f"/workspaces/{ws_id}/analytics/campaigns", cookies=setup["cookies"])
    assert resp.status_code == 200
    campaigns = resp.json()["campaigns"]
    assert len(campaigns) == 1
    row = campaigns[0]
    assert row["replied"]["count"] == 2
    assert row["replied"]["rate"] == 14.29


def test_uniqueness_multiple_opens_count_as_one(client, db, setup):
    """
    A single lead who generates 5 open events must count as 1 unique open,
    and open_rate must reflect that single unique open.
    """
    ws_id = setup["workspace_id"]
    campaign = make_campaign(db, ws_id, status="active")
    sender = make_sender_account(db, ws_id)
    lead = make_lead(db, campaign.campaign_id)

    # 1 sent event → delivered = 1
    make_email_event(db, lead.lead_id, "sent", sender.account_id)
    # 5 open events for the same lead
    for _ in range(5):
        make_email_event(db, lead.lead_id, "opened", sender.account_id)

    resp = client.get(f"/workspaces/{ws_id}/analytics/summary", cookies=setup["cookies"])
    assert resp.status_code == 200
    data = resp.json()
    # unique_opens = 1, total_delivered = 1 → open_rate = 100.0
    assert data["open_rate"] == 100.0
    assert data["total_sent"] == 1


def test_unique_clicks_deduplicated_per_campaign(client, db, setup):
    """
    A lead who clicks 10 times in one campaign counts as 1 unique click.
    click_rate = (1 / 1) * 100 = 100.0.
    """
    ws_id = setup["workspace_id"]
    campaign = make_campaign(db, ws_id, status="active")
    sender = make_sender_account(db, ws_id)
    lead = make_lead(db, campaign.campaign_id)

    make_email_event(db, lead.lead_id, "sent", sender.account_id)
    for _ in range(10):
        make_email_event(db, lead.lead_id, "clicked", sender.account_id)

    resp = client.get(f"/workspaces/{ws_id}/analytics/summary", cookies=setup["cookies"])
    assert resp.status_code == 200
    assert resp.json()["click_rate"] == 100.0


def test_sequence_started_requires_step1_sent_event(client, db, setup):
    """
    sequence_started must count only leads who received a step_number=1 sent event.
    A lead who is enrolled (Lead row exists) but has no sent event on step 1
    must NOT be counted in sequence_started.
    """
    ws_id = setup["workspace_id"]
    campaign = make_campaign(db, ws_id, status="active")
    step1 = make_step(db, campaign.campaign_id, step_number=1)
    step2 = make_step(db, campaign.campaign_id, step_number=2)
    sender = make_sender_account(db, ws_id)

    # lead_a: enrolled AND has step-1 sent → counted
    lead_a = make_lead(db, campaign.campaign_id)
    make_email_event(db, lead_a.lead_id, "sent", sender.account_id, step1.step_id)

    # lead_b: enrolled but only has step-2 sent (skipped step 1) → NOT counted
    lead_b = make_lead(db, campaign.campaign_id)
    make_email_event(db, lead_b.lead_id, "sent", sender.account_id, step2.step_id)

    # lead_c: enrolled, no sent events at all → NOT counted
    _lead_c = make_lead(db, campaign.campaign_id)

    resp = client.get(f"/workspaces/{ws_id}/analytics/campaigns", cookies=setup["cookies"])
    assert resp.status_code == 200
    row = resp.json()["campaigns"][0]
    assert row["sequence_started"] == 1


# ===========================================================================
# Edge Case Tests
# ===========================================================================


def test_campaign_zero_replies_returns_zero_replied_stats(client, db, setup):
    """Campaign with no reply events → replied: {count: 0, rate: 0.00}."""
    ws_id = setup["workspace_id"]
    campaign = make_campaign(db, ws_id, status="active")
    step1 = make_step(db, campaign.campaign_id, step_number=1)
    sender = make_sender_account(db, ws_id)
    lead = make_lead(db, campaign.campaign_id)
    make_email_event(db, lead.lead_id, "sent", sender.account_id, step1.step_id)

    resp = client.get(f"/workspaces/{ws_id}/analytics/campaigns", cookies=setup["cookies"])
    assert resp.status_code == 200
    row = resp.json()["campaigns"][0]
    assert row["replied"]["count"] == 0
    assert row["replied"]["rate"] == 0.0


def test_account_performance_no_sends_returns_zeros_not_null(client, db, setup):
    """
    When a sender account has no events for a campaign, all numeric fields
    must be 0 (integer), never null.
    The account will not appear in results (it never sent anything),
    so account_performance is an empty list — not a list containing nulls.
    """
    ws_id = setup["workspace_id"]
    campaign = make_campaign(db, ws_id, status="active")

    resp = client.get(
        f"/workspaces/{ws_id}/analytics/account-performance",
        params={"campaign_id": campaign.campaign_id},
        cookies=setup["cookies"],
    )
    assert resp.status_code == 200
    rows = resp.json()["account_performance"]
    # No sends → empty list (not a list of nulls)
    assert rows == []


def test_account_performance_row_fields_are_integers_not_null(client, db, setup):
    """
    When a sender account HAS sent emails, all count fields are integers >= 0,
    never null.
    """
    ws_id = setup["workspace_id"]
    campaign = make_campaign(db, ws_id, status="active")
    sender = make_sender_account(db, ws_id)
    lead = make_lead(db, campaign.campaign_id)
    make_email_event(db, lead.lead_id, "sent", sender.account_id)

    resp = client.get(
        f"/workspaces/{ws_id}/analytics/account-performance",
        params={"campaign_id": campaign.campaign_id},
        cookies=setup["cookies"],
    )
    assert resp.status_code == 200
    rows = resp.json()["account_performance"]
    assert len(rows) == 1
    row = rows[0]
    assert row["contacted"] is not None and isinstance(row["contacted"], int)
    assert row["opened"] is not None and isinstance(row["opened"], int)
    assert row["replied"] is not None and isinstance(row["replied"], int)
    assert row["contacted"] == 1
    assert row["opened"] == 0
    assert row["replied"] == 0


def test_graph_no_data_returns_empty_values_not_error(client, db, setup):
    """Graph endpoint with no events → values: [] for all 4 series, HTTP 200."""
    ws_id = setup["workspace_id"]
    resp = client.get(
        f"/workspaces/{ws_id}/analytics/graph",
        params={"granularity": "monthly"},
        cookies=setup["cookies"],
    )
    assert resp.status_code == 200
    gd = resp.json()["graph_data"]
    assert gd["labels"] == []
    for series in gd["series"]:
        assert series["values"] == []


def test_tracking_enabled_true_when_campaign_tracking_is_on(client, db, setup):
    """
    tracking_enabled must be True in account_performance rows when the
    campaign's open_tracking_enabled flag is True (the default).
    """
    ws_id = setup["workspace_id"]
    campaign = make_campaign(db, ws_id, status="active", open_tracking_enabled=True)
    sender = make_sender_account(db, ws_id)
    lead = make_lead(db, campaign.campaign_id)
    make_email_event(db, lead.lead_id, "sent", sender.account_id)

    resp = client.get(
        f"/workspaces/{ws_id}/analytics/account-performance",
        params={"campaign_id": campaign.campaign_id},
        cookies=setup["cookies"],
    )
    assert resp.status_code == 200
    rows = resp.json()["account_performance"]
    assert len(rows) == 1
    assert "tracking_enabled" in rows[0]
    assert rows[0]["tracking_enabled"] is True


# ===========================================================================
# API Tests
# ===========================================================================


def test_graph_returns_exactly_4_series_with_correct_keys(client, db, setup):
    """
    The graph endpoint must return exactly 4 series.
    Keys must be: total_sent, open_rate, click_rate, reply_rate — in that order.
    """
    ws_id = setup["workspace_id"]
    resp = client.get(
        f"/workspaces/{ws_id}/analytics/graph",
        params={"granularity": "monthly"},
        cookies=setup["cookies"],
    )
    assert resp.status_code == 200
    series = resp.json()["graph_data"]["series"]
    assert len(series) == 4
    keys = [s["key"] for s in series]
    assert keys == ["total_sent", "open_rate", "click_rate", "reply_rate"]


def test_campaign_status_only_active_or_completed(client, db, setup):
    """
    Every campaign row in the analytics response must have status
    equal to 'active' or 'completed' — no other value is permitted.
    """
    ws_id = setup["workspace_id"]
    allowed = {"active", "completed"}

    # Create campaigns covering all DB status values.
    db_statuses = ["draft", "scheduled", "active", "paused", "completed", "archived"]
    for i, st in enumerate(db_statuses):
        make_campaign(db, ws_id, name=f"Campaign {i}", status=st)

    resp = client.get(f"/workspaces/{ws_id}/analytics/campaigns", cookies=setup["cookies"])
    assert resp.status_code == 200
    for row in resp.json()["campaigns"]:
        assert row["status"] in allowed, f"Unexpected status: {row['status']}"


def test_account_performance_scoped_to_requested_campaign(client, db, setup):
    """
    Events from campaign_b must NOT appear when requesting account performance
    for campaign_a. The response must reflect only campaign_a's data.
    """
    ws_id = setup["workspace_id"]
    campaign_a = make_campaign(db, ws_id, name="Campaign A", status="active")
    campaign_b = make_campaign(db, ws_id, name="Campaign B", status="active")

    sender_a = make_sender_account(db, ws_id, email="sender_a@example.com")
    sender_b = make_sender_account(db, ws_id, email="sender_b@example.com")

    lead_a = make_lead(db, campaign_a.campaign_id)
    lead_b = make_lead(db, campaign_b.campaign_id)

    # sender_a only sends in campaign_a; sender_b only sends in campaign_b
    make_email_event(db, lead_a.lead_id, "sent", sender_a.account_id)
    make_email_event(db, lead_b.lead_id, "sent", sender_b.account_id)

    resp = client.get(
        f"/workspaces/{ws_id}/analytics/account-performance",
        params={"campaign_id": campaign_a.campaign_id},
        cookies=setup["cookies"],
    )
    assert resp.status_code == 200
    rows = resp.json()["account_performance"]

    accounts_returned = {r["sending_account"] for r in rows}
    # Only sender_a should appear; sender_b is from campaign_b
    assert "sender_a@example.com" in accounts_returned
    assert "sender_b@example.com" not in accounts_returned


# ===========================================================================
# SC-REQUEST #1 — is_opportunity tests
# ===========================================================================


def test_opportunities_counts_only_flagged_leads(client, db, setup):
    """
    opportunities must equal the count of leads where is_opportunity=True.
    Leads with is_opportunity=False must not be counted.
    """
    ws_id = setup["workspace_id"]
    campaign = make_campaign(db, ws_id, status="active")
    step1 = make_step(db, campaign.campaign_id, step_number=1)
    sender = make_sender_account(db, ws_id)

    # 3 leads: 2 flagged as opportunities, 1 not
    opp_lead_1 = make_lead(db, campaign.campaign_id, is_opportunity=True)
    opp_lead_2 = make_lead(db, campaign.campaign_id, is_opportunity=True)
    regular_lead = make_lead(db, campaign.campaign_id, is_opportunity=False)

    for lead in (opp_lead_1, opp_lead_2, regular_lead):
        make_email_event(db, lead.lead_id, "sent", sender.account_id, step1.step_id)

    resp = client.get(f"/workspaces/{ws_id}/analytics/campaigns", cookies=setup["cookies"])
    assert resp.status_code == 200
    row = resp.json()["campaigns"][0]
    assert row["opportunities"] == 2


def test_opportunities_zero_when_no_leads_flagged(client, db, setup):
    """
    opportunities must be 0 when no leads in the campaign have is_opportunity=True.
    """
    ws_id = setup["workspace_id"]
    campaign = make_campaign(db, ws_id, status="active")
    step1 = make_step(db, campaign.campaign_id, step_number=1)
    sender = make_sender_account(db, ws_id)

    lead = make_lead(db, campaign.campaign_id, is_opportunity=False)
    make_email_event(db, lead.lead_id, "sent", sender.account_id, step1.step_id)

    resp = client.get(f"/workspaces/{ws_id}/analytics/campaigns", cookies=setup["cookies"])
    assert resp.status_code == 200
    assert resp.json()["campaigns"][0]["opportunities"] == 0


# ===========================================================================
# SC-REQUEST #2 — open_tracking_enabled tests
# ===========================================================================


def test_tracking_disabled_returns_opened_zero_and_flag_false(client, db, setup):
    """
    When campaign.open_tracking_enabled=False:
      - account_performance rows must have opened=0
      - tracking_enabled must be False
    Even if open events exist in the DB, they must be suppressed.
    """
    ws_id = setup["workspace_id"]
    campaign = make_campaign(db, ws_id, status="active", open_tracking_enabled=False)
    sender = make_sender_account(db, ws_id)
    lead = make_lead(db, campaign.campaign_id)

    make_email_event(db, lead.lead_id, "sent", sender.account_id)
    # An open event exists but tracking is disabled — should be ignored
    make_email_event(db, lead.lead_id, "opened", sender.account_id)

    resp = client.get(
        f"/workspaces/{ws_id}/analytics/account-performance",
        params={"campaign_id": campaign.campaign_id},
        cookies=setup["cookies"],
    )
    assert resp.status_code == 200
    rows = resp.json()["account_performance"]
    assert len(rows) == 1
    assert rows[0]["opened"] == 0
    assert rows[0]["tracking_enabled"] is False


def test_campaign_analytics_opened_zero_when_tracking_disabled(client, db, setup):
    """
    When campaign.open_tracking_enabled=False, the campaign analytics
    opened field must be 0 even if open events exist in the DB.
    """
    ws_id = setup["workspace_id"]
    campaign = make_campaign(db, ws_id, status="active", open_tracking_enabled=False)
    step1 = make_step(db, campaign.campaign_id, step_number=1)
    sender = make_sender_account(db, ws_id)
    lead = make_lead(db, campaign.campaign_id)

    make_email_event(db, lead.lead_id, "sent", sender.account_id, step1.step_id)
    make_email_event(db, lead.lead_id, "opened", sender.account_id)

    resp = client.get(f"/workspaces/{ws_id}/analytics/campaigns", cookies=setup["cookies"])
    assert resp.status_code == 200
    row = resp.json()["campaigns"][0]
    assert row["opened"] == 0
