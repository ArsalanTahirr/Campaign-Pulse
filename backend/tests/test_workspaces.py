"""
tests/test_workspaces.py — Workspace creation, listing, and permission checks.
"""

import pytest
from tests.factories import auth_cookies, make_user, make_workspace


@pytest.fixture
def user(db):
    return make_user(db)


def test_create_workspace(client, db, user):
    res = client.post(
        "/workspaces",
        json={"name": "Acme Corp"},
        cookies=auth_cookies(user),
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Acme Corp"
    assert "workspace_id" in data


def test_list_workspaces_includes_created(client, db, user):
    make_workspace(db, user)
    res = client.get("/workspaces", cookies=auth_cookies(user))
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_list_workspaces_excludes_others(client, db, user):
    other = make_user(db)
    other_ws = make_workspace(db, other)
    res = client.get("/workspaces", cookies=auth_cookies(user))
    assert res.status_code == 200
    ids_returned = {w["workspace_id"] for w in res.json()}
    assert other_ws.workspace_id not in ids_returned


def test_get_workspace_as_member(client, db, user):
    ws = make_workspace(db, user)
    res = client.get(f"/workspaces/{ws.workspace_id}", cookies=auth_cookies(user))
    assert res.status_code == 200
    assert res.json()["workspace_id"] == ws.workspace_id


def test_get_workspace_non_member_forbidden(client, db, user):
    other = make_user(db)
    ws = make_workspace(db, other)
    res = client.get(f"/workspaces/{ws.workspace_id}", cookies=auth_cookies(user))
    assert res.status_code == 403


def test_rename_workspace_owner(client, db, user):
    ws = make_workspace(db, user)
    res = client.patch(
        f"/workspaces/{ws.workspace_id}",
        json={"name": "Renamed Corp"},
        cookies=auth_cookies(user),
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Renamed Corp"


def test_create_workspace_unauthenticated(client):
    res = client.post("/workspaces", json={"name": "No Auth"})
    assert res.status_code == 401


def test_workspace_name_too_short(client, db, user):
    res = client.post("/workspaces", json={"name": "A"}, cookies=auth_cookies(user))
    assert res.status_code == 422
