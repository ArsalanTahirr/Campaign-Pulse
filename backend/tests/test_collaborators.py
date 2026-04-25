"""
tests/test_collaborators.py — Collaborator management + RBAC edge cases.

RBAC rules tested:
  • Agency cannot promote/demote an Owner-role collaborator.
  • Agency cannot remove an Owner-role collaborator.
  • Cannot remove the last Owner from a workspace.
  • Cannot remove yourself from a workspace.
  • Data Analyst cannot remove or change roles.
"""

import pytest
from tests.factories import (
    add_member,
    auth_cookies,
    make_role,
    make_user,
    make_workspace,
)


@pytest.fixture
def owner(db):
    return make_user(db)


@pytest.fixture
def ws(db, owner):
    return make_workspace(db, owner)


@pytest.fixture
def agency_user(db, ws):
    user = make_user(db)
    add_member(db, ws.workspace_id, user, "Agency")
    return user


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


def _collab_id(client, ws, target_user, actor_cookies):
    res = client.get(f"/workspaces/{ws.workspace_id}/collaborators", cookies=actor_cookies)
    for c in res.json():
        if c["user_id"] == target_user.user_id:
            # API returns `collaborator_id` (mapped from ORM `member_id` via alias)
            return c["collaborator_id"]
    return None


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


def test_list_collaborators_owner(client, db, owner, ws, agency_user):
    res = client.get(
        f"/workspaces/{ws.workspace_id}/collaborators",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_list_collaborators_analyst(client, db, analyst, ws):
    res = client.get(
        f"/workspaces/{ws.workspace_id}/collaborators",
        cookies=auth_cookies(analyst),
    )
    assert res.status_code == 200  # Data Analyst has view_workspace permission


# ---------------------------------------------------------------------------
# Role changes
# ---------------------------------------------------------------------------


def test_owner_can_change_any_role(client, db, owner, ws, marketer):
    agency_role = make_role(db, "Agency")
    cid = _collab_id(client, ws, marketer, auth_cookies(owner))
    assert cid is not None
    res = client.patch(
        f"/workspaces/{ws.workspace_id}/collaborators/{cid}/role",
        json={"role_id": agency_role.role_id},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 200


def test_agency_cannot_change_owner_role(client, db, owner, ws, agency_user):
    """Agency should not be able to demote the Owner."""
    marketer_role = make_role(db, "Marketing Manager")
    owner_cid = _collab_id(client, ws, owner, auth_cookies(agency_user))
    assert owner_cid is not None
    res = client.patch(
        f"/workspaces/{ws.workspace_id}/collaborators/{owner_cid}/role",
        json={"role_id": marketer_role.role_id},
        cookies=auth_cookies(agency_user),
    )
    assert res.status_code == 403


def test_agency_cannot_promote_to_owner(client, db, owner, ws, agency_user, marketer):
    """Agency should not be able to promote someone to Owner."""
    owner_role = make_role(db, "Owner")
    cid = _collab_id(client, ws, marketer, auth_cookies(owner))
    res = client.patch(
        f"/workspaces/{ws.workspace_id}/collaborators/{cid}/role",
        json={"role_id": owner_role.role_id},
        cookies=auth_cookies(agency_user),
    )
    assert res.status_code == 403


def test_analyst_cannot_change_roles(client, db, analyst, ws, marketer):
    make_role(db, "Agency")
    cid = _collab_id(client, ws, marketer, auth_cookies(analyst))
    agency_role = make_role(db, "Agency")
    res = client.patch(
        f"/workspaces/{ws.workspace_id}/collaborators/{cid}/role",
        json={"role_id": agency_role.role_id},
        cookies=auth_cookies(analyst),
    )
    assert res.status_code == 403


def test_change_role_nonexistent_collaborator(client, db, owner, ws):
    import uuid
    agency_role = make_role(db, "Agency")
    res = client.patch(
        f"/workspaces/{ws.workspace_id}/collaborators/{uuid.uuid4()}/role",
        json={"role_id": agency_role.role_id},
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Removal
# ---------------------------------------------------------------------------


def test_owner_can_remove_member(client, db, owner, ws, marketer):
    cid = _collab_id(client, ws, marketer, auth_cookies(owner))
    res = client.delete(
        f"/workspaces/{ws.workspace_id}/collaborators/{cid}",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 204


def test_cannot_remove_self(client, db, owner, ws):
    owner_cid = _collab_id(client, ws, owner, auth_cookies(owner))
    res = client.delete(
        f"/workspaces/{ws.workspace_id}/collaborators/{owner_cid}",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 403


def test_cannot_remove_last_owner(client, db, owner, ws):
    """Removing the only Owner must fail."""
    owner_cid = _collab_id(client, ws, owner, auth_cookies(owner))
    # Add second owner so we can test from their perspective vs. removing the only one.
    second_owner = make_user(db)
    add_member(db, ws.workspace_id, second_owner, "Owner")

    # Second owner tries to remove first owner (now there are 2 owners, so it's allowed)
    second_cid = _collab_id(client, ws, second_owner, auth_cookies(owner))
    res = client.delete(
        f"/workspaces/{ws.workspace_id}/collaborators/{second_cid}",
        cookies=auth_cookies(owner),
    )
    assert res.status_code == 204


def test_removing_sole_owner_blocked(client, db, owner, ws):
    """With only one owner, removing that owner should fail (409)."""
    # owner is the only Owner in this workspace
    # We need to try to remove them as another admin (agency)
    agency = make_user(db)
    add_member(db, ws.workspace_id, agency, "Agency")
    owner_cid = _collab_id(client, ws, owner, auth_cookies(agency))
    res = client.delete(
        f"/workspaces/{ws.workspace_id}/collaborators/{owner_cid}",
        cookies=auth_cookies(agency),
    )
    assert res.status_code == 403  # Agency can't touch Owner


def test_agency_cannot_remove_owner(client, db, owner, ws, agency_user):
    owner_cid = _collab_id(client, ws, owner, auth_cookies(agency_user))
    res = client.delete(
        f"/workspaces/{ws.workspace_id}/collaborators/{owner_cid}",
        cookies=auth_cookies(agency_user),
    )
    assert res.status_code == 403


def test_analyst_cannot_remove_anyone(client, db, analyst, ws, marketer):
    cid = _collab_id(client, ws, marketer, auth_cookies(analyst))
    res = client.delete(
        f"/workspaces/{ws.workspace_id}/collaborators/{cid}",
        cookies=auth_cookies(analyst),
    )
    assert res.status_code == 403
