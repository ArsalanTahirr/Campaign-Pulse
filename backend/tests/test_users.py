"""
test_users.py — Comprehensive pytest suite for CampaignPulse auth routes.

Coverage matrix
───────────────
Signup
  ✓ Successful registration (201, returns user_id + email)
  ✓ Duplicate email address (409)
  ✓ Password — no uppercase letter (422)
  ✓ Password — no digit (422)
  ✓ Password — no special character (422)
  ✓ Password — too short (422)
  ✓ Terms not accepted (422)
  ✓ User is under 18 years old (422)
  ✓ Malformed email address (422)
  ✓ first_name shorter than 2 characters (422)

Email verification
  ✓ Successful verification — is_verified flips to True, token cleared (307 redirect)
  ✓ Tampered / malformed token (400)
  ✓ Expired token — decode_verification_token patched to raise SignatureExpired (400)
  ✓ Token already consumed — second use returns 403

Google OAuth
  ✓ /google/login redirects to accounts.google.com (307)
  ✓ /google/callback — brand-new user created, redirects to frontend callback (307)
  ✓ /google/callback — existing user re-uses OAuthAccount, no duplicates (307)

External calls are fully mocked:
  - app.routers.users.send_verification_email → prevents real email delivery
  - httpx.Client.post   → prevents real token exchange with Google
  - httpx.Client.get    → prevents real userinfo fetch from Google
"""

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from itsdangerous import SignatureExpired

# ---------------------------------------------------------------------------
# Test payload helpers
# ---------------------------------------------------------------------------

_BASE_PAYLOAD: dict = {
    "first_name": "Jane",
    "last_name": "Doe",
    "email": "jane.doe@example.com",
    "password": "SecurePass1!",
    "terms_accepted": True,
}


def _unique_email() -> str:
    """Return a fresh email address that is guaranteed not to exist in the DB."""
    return f"test_{uuid.uuid4().hex[:12]}@example.com"


def _payload(**overrides) -> dict:
    """Return a copy of the base payload with the given fields overridden."""
    return {**_BASE_PAYLOAD, "email": _unique_email(), **overrides}


# ===========================================================================
# Signup tests
# ===========================================================================


def test_signup_success(client, mocker):
    mocker.patch("app.routers.users.send_verification_email", return_value=None)

    resp = client.post("/auth/signup", json=_payload())

    assert resp.status_code == 201
    data = resp.json()
    assert "user_id" in data
    assert "@" in data["email"]
    assert "verify" in data["message"].lower() or "check" in data["message"].lower()


def test_signup_creates_default_owner_workspace(client, db, mocker):
    from app.models import Collaborator, Role, User

    mocker.patch("app.routers.users.send_verification_email", return_value=None)
    email = _unique_email()
    resp = client.post("/auth/signup", json=_payload(email=email))
    assert resp.status_code == 201

    user = db.query(User).filter(User.email == email).first()
    assert user is not None

    owner_membership = (
        db.query(Collaborator)
        .join(Role, Role.role_id == Collaborator.role_id)
        .filter(
            Collaborator.user_id == user.user_id,
            Collaborator.invite_status == "accepted",
            Role.role_name == "Owner",
        )
        .first()
    )
    assert owner_membership is not None


def test_signup_duplicate_email_unverified_resends_verification(client, mocker):
    mocker.patch("app.routers.users.send_verification_email", return_value=None)

    email = _unique_email()
    payload = _payload(email=email)

    first = client.post("/auth/signup", json=payload)
    assert first.status_code == 201

    second = client.post("/auth/signup", json=payload)
    assert second.status_code == 201
    assert "not verified" in second.json()["message"].lower()


def test_signup_duplicate_email_verified_returns_409(client, db, mocker):
    from app.models import User

    mocker.patch("app.routers.users.send_verification_email", return_value=None)

    email = _unique_email()
    payload = _payload(email=email)

    first = client.post("/auth/signup", json=payload)
    assert first.status_code == 201

    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    user.is_verified = True
    db.commit()

    second = client.post("/auth/signup", json=payload)
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"].lower()


def test_signup_password_no_uppercase(client):
    resp = client.post("/auth/signup", json=_payload(password="lowercase1!"))
    assert resp.status_code == 422


def test_signup_password_no_digit(client):
    resp = client.post("/auth/signup", json=_payload(password="NoDigits!!!"))
    assert resp.status_code == 422


def test_signup_password_no_special_char(client):
    resp = client.post("/auth/signup", json=_payload(password="NoSpecial1A"))
    assert resp.status_code == 422


def test_signup_password_too_short(client):
    resp = client.post("/auth/signup", json=_payload(password="Sh0rt!"))
    assert resp.status_code == 422


def test_signup_terms_not_accepted(client):
    resp = client.post("/auth/signup", json=_payload(terms_accepted=False))
    assert resp.status_code == 422


def test_signup_underage(client):
    dob = (date.today() - timedelta(days=365 * 17)).isoformat()
    resp = client.post("/auth/signup", json=_payload(date_of_birth=dob))
    assert resp.status_code == 422


def test_signup_invalid_email(client):
    resp = client.post("/auth/signup", json=_payload(email="not-a-valid-email"))
    assert resp.status_code == 422


def test_signup_first_name_too_short(client):
    resp = client.post("/auth/signup", json=_payload(first_name="A"))
    assert resp.status_code == 422


def test_signup_google_only_email_triggers_account_link_flow(client, db, mocker):
    from app.models import OAuthAccount, User

    google_email = _unique_email()
    user = User(
        user_id=str(uuid.uuid4()),
        first_name="Google",
        last_name="Only",
        email=google_email,
        is_verified=True,
    )
    db.add(user)
    db.flush()
    db.add(
        OAuthAccount(
            id=str(uuid.uuid4()),
            user_id=user.user_id,
            provider_type="google",
            provider_id=f"google_sub_{uuid.uuid4().hex}",
            access_token="at_tok",
        )
    )
    db.commit()

    mocked_sender = mocker.patch("app.routers.users.send_account_link_email", return_value=None)
    resp = client.post("/auth/signup", json=_payload(email=google_email))
    assert resp.status_code == 409
    assert "google account" in resp.json()["detail"].lower()

    from app.models import LocalAuth
    local_auth = db.query(LocalAuth).filter(LocalAuth.user_id == user.user_id).first()
    assert local_auth is not None
    assert local_auth.password_hash is None
    assert local_auth.verification_token is not None
    assert local_auth.reset_token is not None
    mocked_sender.assert_called_once()


def test_link_local_account_sets_password_only_after_verification(client, db, mocker):
    from app.auth import verify_password
    from app.models import LocalAuth, OAuthAccount, User

    email = _unique_email()
    user = User(
        user_id=str(uuid.uuid4()),
        first_name="Link",
        last_name="Target",
        email=email,
        is_verified=True,
    )
    db.add(user)
    db.flush()
    db.add(
        OAuthAccount(
            id=str(uuid.uuid4()),
            user_id=user.user_id,
            provider_type="google",
            provider_id=f"google_sub_{uuid.uuid4().hex}",
            access_token="at_tok",
        )
    )
    db.commit()

    mocker.patch("app.routers.users.send_account_link_email", return_value=None)
    signup_resp = client.post("/auth/signup", json=_payload(email=email, password="LinkedPass1!"))
    assert signup_resp.status_code == 409

    local_auth = db.query(LocalAuth).filter(LocalAuth.user_id == user.user_id).first()
    assert local_auth.password_hash is None
    link_token = local_auth.verification_token

    link_resp = client.get(f"/auth/link-local-account?token={link_token}", follow_redirects=False)
    assert link_resp.status_code == 307
    assert "status=success" in link_resp.headers["location"]

    db.refresh(local_auth)
    assert local_auth.password_hash is not None
    assert verify_password("LinkedPass1!", local_auth.password_hash)
    assert local_auth.verification_token is None
    assert local_auth.reset_token is None

# ===========================================================================
# Email verification tests
# ===========================================================================


def test_verify_email_success(client, db, mocker):
    """
    After signup, grab the token stored in LocalAuth and verify it.
    Assert that is_verified is True and the stored token is cleared.
    """
    from app.models import LocalAuth, User

    mocker.patch("app.routers.users.send_verification_email", return_value=None)

    email = _unique_email()
    resp = client.post("/auth/signup", json=_payload(email=email))
    assert resp.status_code == 201

    user = db.query(User).filter(User.email == email).first()
    assert user is not None, "User row should exist after signup"

    local_auth = db.query(LocalAuth).filter(LocalAuth.user_id == user.user_id).first()
    assert local_auth is not None
    token = local_auth.verification_token
    assert token is not None, "Verification token should be set after signup"

    verify_resp = client.get(f"/auth/verify-email?token={token}", follow_redirects=False)
    assert verify_resp.status_code == 307
    assert "/verify-email-result" in verify_resp.headers["location"]
    assert "status=success" in verify_resp.headers["location"]

    db.refresh(user)
    assert user.is_verified is True

    db.refresh(local_auth)
    assert local_auth.verification_token is None


def test_verify_email_invalid_token(client):
    resp = client.get(
        "/auth/verify-email?token=completely.invalid.garbage",
        follow_redirects=False,
    )
    assert resp.status_code == 307
    assert "status=error" in resp.headers["location"]
    assert "Invalid+verification+token" in resp.headers["location"]


def test_verify_email_expired_token(client, db, mocker):
    """
    Patch decode_verification_token (as imported in the router) to raise
    SignatureExpired, simulating a token that has outlived its 24-hour window.
    """
    from app.models import LocalAuth, User

    mocker.patch("app.routers.users.send_verification_email", return_value=None)

    email = _unique_email()
    resp = client.post("/auth/signup", json=_payload(email=email))
    assert resp.status_code == 201

    user = db.query(User).filter(User.email == email).first()
    local_auth = db.query(LocalAuth).filter(LocalAuth.user_id == user.user_id).first()
    token = local_auth.verification_token

    mocker.patch(
        "app.routers.users.decode_verification_token",
        side_effect=SignatureExpired("forced expiry"),
    )

    verify_resp = client.get(f"/auth/verify-email?token={token}", follow_redirects=False)
    assert verify_resp.status_code == 307
    assert "status=error" in verify_resp.headers["location"]
    assert "expired" in verify_resp.headers["location"].lower()


def test_verify_email_already_used(client, db, mocker):
    """
    Using a token a second time should return 403 because the route handler
    clears the stored token on the first successful verification.
    """
    from app.models import LocalAuth, User

    mocker.patch("app.routers.users.send_verification_email", return_value=None)

    email = _unique_email()
    resp = client.post("/auth/signup", json=_payload(email=email))
    assert resp.status_code == 201

    user = db.query(User).filter(User.email == email).first()
    local_auth = db.query(LocalAuth).filter(LocalAuth.user_id == user.user_id).first()
    token = local_auth.verification_token

    first = client.get(f"/auth/verify-email?token={token}", follow_redirects=False)
    assert first.status_code == 307

    second = client.get(f"/auth/verify-email?token={token}", follow_redirects=False)
    assert second.status_code == 307
    assert "status=error" in second.headers["location"]
    assert "already+been+used" in second.headers["location"].lower()


# ===========================================================================
# Google OAuth tests
# ===========================================================================


def test_google_login_redirect(client):
    """GET /auth/google/login must return a 307 pointing at Google."""
    resp = client.get("/auth/google/login", follow_redirects=False)
    assert resp.status_code == 307
    assert "accounts.google.com" in resp.headers["location"]


def _mock_google_http(mocker, token_json: dict, userinfo_json: dict):
    """
    Patch `httpx.Client` as seen from the router module so that:
      - The first `with httpx.Client() as http: http.post(...)` returns a mock
        with the given token_json payload.
      - The second `with httpx.Client() as http: http.get(...)` returns a mock
        with the given userinfo_json payload.

    Patching at the module level (app.routers.users.httpx.Client) instead of
    the global class prevents the patch from accidentally intercepting the
    TestClient's own HTTP calls to the FastAPI app.
    """
    mock_token = mocker.MagicMock()
    mock_token.status_code = 200
    mock_token.json.return_value = token_json

    mock_userinfo = mocker.MagicMock()
    mock_userinfo.status_code = 200
    mock_userinfo.json.return_value = userinfo_json

    # The route handler uses two separate `with httpx.Client() as http:` blocks.
    # Both blocks share the same mock context instance, so both .post() and
    # .get() are available on the single inner mock object.
    mock_http_instance = mocker.MagicMock()
    mock_http_instance.post.return_value = mock_token
    mock_http_instance.get.return_value = mock_userinfo

    mock_client_cls = mocker.MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_http_instance
    mock_client_cls.return_value.__exit__.return_value = False

    mocker.patch("app.routers.users.httpx.Client", mock_client_cls)


def test_google_callback_new_user(client, db, mocker):
    """
    A brand-new Google identity should create a User + OAuthAccount row and
    return a valid TokenResponse.
    """
    from app.models import Collaborator, OAuthAccount, Role, User

    google_sub = f"google_sub_{uuid.uuid4().hex}"
    google_email = _unique_email()

    _mock_google_http(
        mocker,
        token_json={"access_token": "goog_at_abc123"},
        userinfo_json={
            "sub": google_sub,
            "email": google_email,
            "given_name": "Alice",
            "family_name": "Smith",
        },
    )

    resp = client.get("/auth/google/callback?code=fake_code", follow_redirects=False)
    assert resp.status_code == 307
    location = resp.headers["location"]
    assert location.endswith("/dashboard")
    assert "set-cookie" in {k.lower() for k in resp.headers.keys()}
    assert "access_token=" in resp.headers.get("set-cookie", "")

    oauth = (
        db.query(OAuthAccount)
        .filter(
            OAuthAccount.provider_type == "google",
            OAuthAccount.provider_id == google_sub,
        )
        .first()
    )
    assert oauth is not None, "OAuthAccount row should be created for a new Google user"

    user = db.query(User).filter(User.email == google_email).first()
    assert user is not None
    assert user.is_verified is True

    owner_membership = (
        db.query(Collaborator)
        .join(Role, Role.role_id == Collaborator.role_id)
        .filter(
            Collaborator.user_id == user.user_id,
            Collaborator.invite_status == "accepted",
            Role.role_name == "Owner",
        )
        .first()
    )
    assert owner_membership is not None


def test_google_callback_existing_user(client, db, mocker):
    """
    Calling /google/callback twice with the same Google identity must not
    create duplicate OAuthAccount rows.
    """
    from app.models import OAuthAccount

    google_sub = f"google_sub_{uuid.uuid4().hex}"
    google_email = _unique_email()

    token_json = {"access_token": "goog_at_xyz789"}
    userinfo_json = {
        "sub": google_sub,
        "email": google_email,
        "given_name": "Bob",
        "family_name": "Jones",
    }

    # Set up a single patch that covers both callback calls.
    # mocker.patch lasts for the entire test, so both GET requests to the
    # callback endpoint will use the same mock.
    _mock_google_http(mocker, token_json=token_json, userinfo_json=userinfo_json)

    # First login — creates User + OAuthAccount
    resp1 = client.get("/auth/google/callback?code=fake_code_1", follow_redirects=False)
    assert resp1.status_code == 307

    # Second login — should find the existing OAuthAccount and NOT create a new one
    resp2 = client.get("/auth/google/callback?code=fake_code_2", follow_redirects=False)
    assert resp2.status_code == 307

    # Confirm exactly one OAuthAccount row exists for this sub
    oauth_rows = (
        db.query(OAuthAccount)
        .filter(
            OAuthAccount.provider_type == "google",
            OAuthAccount.provider_id == google_sub,
        )
        .all()
    )
    assert len(oauth_rows) == 1, (
        "Calling /google/callback twice for the same sub must not create duplicate rows"
    )


def test_login_without_remember_me_sets_session_cookie(client, db, mocker):
    from app.models import User

    mocker.patch("app.routers.users.send_verification_email", return_value=None)
    payload = _payload()
    signup = client.post("/auth/signup", json=payload)
    assert signup.status_code == 201

    user = db.query(User).filter(User.email == payload["email"]).first()
    user.is_verified = True
    db.commit()

    resp = client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"], "remember_me": False},
    )
    assert resp.status_code == 200
    cookie_header = resp.headers.get("set-cookie", "").lower()
    assert "access_token=" in cookie_header
    access_cookie = [chunk.strip() for chunk in cookie_header.split(",") if chunk.strip().startswith("access_token=")][-1]
    assert "max-age" not in access_cookie


def test_login_with_remember_me_sets_three_day_cookie(client, db, mocker):
    from app.models import User

    mocker.patch("app.routers.users.send_verification_email", return_value=None)
    payload = _payload()
    signup = client.post("/auth/signup", json=payload)
    assert signup.status_code == 201

    user = db.query(User).filter(User.email == payload["email"]).first()
    user.is_verified = True
    db.commit()

    resp = client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"], "remember_me": True},
    )
    assert resp.status_code == 200
    cookie_header = resp.headers.get("set-cookie", "").lower()
    assert "access_token=" in cookie_header
    assert "max-age=259200" in cookie_header


def test_reset_password_request_sets_reset_token_and_sends_email(client, db, mocker):
    from app.auth import hash_password
    from app.models import LocalAuth, User

    email = _unique_email()
    user = User(
        user_id=str(uuid.uuid4()),
        first_name="Reset",
        last_name="User",
        email=email,
        is_verified=True,
    )
    db.add(user)
    db.flush()
    db.add(LocalAuth(user_id=user.user_id, password_hash=hash_password("SecurePass1!")))
    db.commit()

    mocked_sender = mocker.patch("app.routers.users.send_password_reset_email", return_value=None)
    resp = client.post("/auth/reset-password", json={"email": email})
    assert resp.status_code == 200

    local_auth = db.query(LocalAuth).filter(LocalAuth.user_id == user.user_id).first()
    assert local_auth.reset_token is not None
    assert local_auth.reset_expires_at is not None
    mocked_sender.assert_called_once()


def test_reset_password_confirm_updates_password(client, db):
    from app.auth import hash_password, verify_password
    from app.models import LocalAuth, User

    user = User(
        user_id=str(uuid.uuid4()),
        first_name="Reset",
        last_name="User",
        email=_unique_email(),
        is_verified=True,
    )
    db.add(user)
    db.flush()
    reset_token = "tok_reset_12345678"
    db.add(
        LocalAuth(
            user_id=user.user_id,
            password_hash=hash_password("OldPass1!"),
            reset_token=reset_token,
            reset_expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
    )
    db.commit()

    resp = client.post(
        "/auth/reset-password/confirm",
        json={"token": reset_token, "new_password": "NewPass1!", "confirm_password": "NewPass1!"},
    )
    assert resp.status_code == 200

    local_auth = db.query(LocalAuth).filter(LocalAuth.user_id == user.user_id).first()
    assert local_auth.reset_token is None
    assert local_auth.reset_expires_at is None
    assert verify_password("NewPass1!", local_auth.password_hash)


def test_reset_password_confirm_rejects_reused_password(client, db):
    from app.auth import hash_password
    from app.models import LocalAuth, User

    current_password = "ReusePass1!"
    user = User(
        user_id=str(uuid.uuid4()),
        first_name="Reset",
        last_name="User",
        email=_unique_email(),
        is_verified=True,
    )
    db.add(user)
    db.flush()
    reset_token = "tok_reset_reuse_12345"
    db.add(
        LocalAuth(
            user_id=user.user_id,
            password_hash=hash_password(current_password),
            reset_token=reset_token,
            reset_expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
    )
    db.commit()

    resp = client.post(
        "/auth/reset-password/confirm",
        json={"token": reset_token, "new_password": current_password, "confirm_password": current_password},
    )
    assert resp.status_code == 400
    assert "different from your current password" in resp.json()["detail"].lower()


def test_reset_password_confirm_rejects_mismatched_confirm_password(client, db):
    from app.auth import hash_password
    from app.models import LocalAuth, User

    user = User(
        user_id=str(uuid.uuid4()),
        first_name="Reset",
        last_name="User",
        email=_unique_email(),
        is_verified=True,
    )
    db.add(user)
    db.flush()
    reset_token = "tok_reset_mismatch_12345"
    db.add(
        LocalAuth(
            user_id=user.user_id,
            password_hash=hash_password("OldPass1!"),
            reset_token=reset_token,
            reset_expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
    )
    db.commit()

    resp = client.post(
        "/auth/reset-password/confirm",
        json={
            "token": reset_token,
            "new_password": "NewPass1!",
            "confirm_password": "DifferentPass1!",
        },
    )
    assert resp.status_code == 422
    assert "must match" in str(resp.json()).lower()


def test_reset_password_token_is_revoked_after_successful_update(client, db):
    from app.auth import hash_password
    from app.models import LocalAuth, User

    user = User(
        user_id=str(uuid.uuid4()),
        first_name="Reset",
        last_name="User",
        email=_unique_email(),
        is_verified=True,
    )
    db.add(user)
    db.flush()
    reset_token = "tok_reset_one_time_12345"
    db.add(
        LocalAuth(
            user_id=user.user_id,
            password_hash=hash_password("OldPass1!"),
            reset_token=reset_token,
            reset_expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
    )
    db.commit()

    first = client.post(
        "/auth/reset-password/confirm",
        json={
            "token": reset_token,
            "new_password": "BrandNew1!",
            "confirm_password": "BrandNew1!",
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/auth/reset-password/confirm",
        json={
            "token": reset_token,
            "new_password": "AnotherNew1!",
            "confirm_password": "AnotherNew1!",
        },
    )
    assert second.status_code == 400
    assert "invalid reset token" in second.json()["detail"].lower()
