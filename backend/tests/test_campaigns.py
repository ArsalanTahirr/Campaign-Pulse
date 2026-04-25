"""
tests/test_campaigns.py — Campaign CRUD + lifecycle transition tests.
"""

import pytest
from tests.factories import (
    add_member,
    auth_cookies,
    make_campaign,
    make_role,
    make_step,
    make_step_email,
    make_user,
    make_workspace,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def owner(db):
    return make_user(db)


@pytest.fixture
def ws(db, owner):
    return make_workspace(db, owner)


@pytest.fixture
def marketer(db, ws):
    user = make_user(db)
    add_member(db, ws.workspace_id, user, "Marketing Manager")
    return user


@pytest.fixture
def analyst(db, ws):
    user = make_user(db)
    add_member(db, ws.workspace_id, user, "Data Analyst")
    return user


# ===========================================================================
# CRUD
# ===========================================================================


def test_create_campaign_owner(client, db, owner, ws):
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns",
        json={"name": "Q2 Outreach"},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Q2 Outreach"
    assert data["status"] == "draft"


def test_create_campaign_marketer_allowed(client, db, marketer, ws):
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns",
        json={"name": "Marketer Campaign"},
        cookies=auth_cookies(marketer),
    )
    assert res.status_code == 201


def test_create_campaign_analyst_forbidden(client, db, analyst, ws):
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns",
        json={"name": "Should Fail"},
        cookies=auth_cookies(analyst),
    )
    assert res.status_code == 403


def test_list_campaigns_returns_counts(client, db, owner, ws):
    campaign = make_campaign(db, ws.workspace_id)
    step = make_step(db, campaign.campaign_id)
    make_step_email(db, step.step_id)

    res = client.get(
        f"/workspaces/{ws.workspace_id}/campaigns",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 200
    found = next((c for c in res.json() if c["campaign_id"] == campaign.campaign_id), None)
    assert found is not None
    assert found["step_count"] == 1


def test_update_campaign_name(client, db, owner, ws):
    campaign = make_campaign(db, ws.workspace_id)
    res = client.patch(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}",
        json={"name": "Renamed"},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Renamed"
    assert res.json()["updated_at"] is not None


def test_delete_campaign_owner(client, db, owner, ws):
    campaign = make_campaign(db, ws.workspace_id)
    res = client.delete(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 204


def test_delete_campaign_marketer_forbidden(client, db, marketer, ws):
    campaign = make_campaign(db, ws.workspace_id)
    res = client.delete(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}",
        cookies=auth_cookies(marketer),
    )
    assert res.status_code == 403


def test_get_campaign_not_found(client, db, owner, ws):
    import uuid
    res = client.get(
        f"/workspaces/{ws.workspace_id}/campaigns/{uuid.uuid4()}",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 404


# ===========================================================================
# Lifecycle transitions
# ===========================================================================


def test_start_draft_campaign(client, db, owner, ws):
    campaign = make_campaign(db, ws.workspace_id, status="draft")
    step = make_step(db, campaign.campaign_id)
    make_step_email(db, step.step_id)

    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/runs",
        json={"action": "started"},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    assert res.json()["run_status"] == "active"


def test_start_campaign_no_variants_fails(client, db, owner, ws):
    """A campaign with steps but no email variants cannot be started."""
    campaign = make_campaign(db, ws.workspace_id, status="draft")
    make_step(db, campaign.campaign_id)  # step has no email_variants

    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/runs",
        json={"action": "started"},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 422
    assert "no email variants" in res.json()["detail"].lower()


def test_pause_running_campaign(client, db, owner, ws):
    campaign = make_campaign(db, ws.workspace_id, status="active")
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/runs",
        json={"action": "paused"},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 201
    assert res.json()["run_status"] == "paused"


def test_cannot_pause_draft_campaign(client, db, owner, ws):
    campaign = make_campaign(db, ws.workspace_id, status="draft")
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/runs",
        json={"action": "paused"},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 409


def test_invalid_action_returns_422(client, db, owner, ws):
    campaign = make_campaign(db, ws.workspace_id, status="draft")
    res = client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/runs",
        json={"action": "explode"},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 422


def test_run_history_recorded(client, db, owner, ws):
    campaign = make_campaign(db, ws.workspace_id, status="active")
    client.post(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/runs",
        json={"action": "paused"},
        cookies=auth_cookies(owner),
    )
    res = client.get(
        f"/workspaces/{ws.workspace_id}/campaigns/{campaign.campaign_id}/runs",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 200
    assert len(res.json()) >= 1
    assert res.json()[0]["action"] == "paused"


def test_unauthenticated_returns_401(client, ws):
    res = client.get(f"/workspaces/{ws.workspace_id}/campaigns")
    assert res.status_code == 401
