"""
routers/users.py — Auth endpoints for CampaignPulse.

All routes are mounted under the /auth prefix by main.py:

    POST  /auth/signup                — local email+password registration
    GET   /auth/verify-email?token=   — email verification via signed token
    GET   /auth/google/login          — initiate Google OAuth 2.0 flow
    GET   /auth/google/callback       — handle Google OAuth callback
"""

import os
import uuid
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urljoin

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.auth import (
    BadSignature,
    SignatureExpired,
    create_access_token,
    decode_access_token,
    decode_verification_token,
    generate_verification_token,
    hash_password,
    JWTError,
    verify_password,
)
from app.database import get_db
from app.email_utils import send_verification_email
from app.models import LocalAuth, OAuthAccount, User
from app.schemas import LoginRequest, SignupRequest, SignupResponse, TokenResponse

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
load_dotenv(dotenv_path=_ENV_PATH)

GOOGLE_CLIENT_ID: str = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET: str = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI: str = os.environ.get("GOOGLE_REDIRECT_URI", "")
BACKEND_BASE_URL: str = os.environ.get("BACKEND_BASE_URL", "http://localhost:8000")
FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:3000")
FRONTEND_VERIFY_EMAIL_PATH: str = os.environ.get(
    "FRONTEND_VERIFY_EMAIL_PATH",
    "/auth/verify-email-result",
)
FRONTEND_OAUTH_CALLBACK_PATH: str = os.environ.get(
    "FRONTEND_OAUTH_CALLBACK_PATH",
    "/auth/oauth/callback",
)
FRONTEND_DASHBOARD_PATH: str = os.environ.get("FRONTEND_DASHBOARD_PATH", "/dashboard")
ACCESS_TOKEN_EXPIRE_SECONDS: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 30)) * 60

AUTH_COOKIE_NAME = "access_token"

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter()
logger = logging.getLogger(__name__)

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def _build_frontend_redirect(path: str, params: dict | None = None, fragment: dict | None = None) -> str:
    """
    Build a frontend redirect URL with optional query parameters and hash.
    Hash payload is used for sensitive values (e.g. access token) so it never
    hits server logs as query parameters.
    """
    base = urljoin(FRONTEND_URL.rstrip("/") + "/", path.lstrip("/"))
    query = f"?{urlencode(params)}" if params else ""
    hash_part = f"#{urlencode(fragment)}" if fragment else ""
    return f"{base}{query}{hash_part}"


def _send_verification_email_safe(
    to_email: str,
    token: str,
    first_name: str,
    base_url: str,
) -> None:
    """
    Never let SMTP/provider errors crash the request lifecycle.
    Background delivery failures are logged for observability.
    """
    try:
        send_verification_email(
            to_email=to_email,
            token=token,
            first_name=first_name,
            base_url=base_url,
        )
    except Exception:
        logger.exception("Failed to send verification email to %s", to_email)


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=ACCESS_TOKEN_EXPIRE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )


def _extract_access_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return request.cookies.get(AUTH_COOKIE_NAME, "")


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = _extract_access_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found for this session.",
        )
    return user


# ===========================================================================
# POST /signup
# ===========================================================================


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user with email and password",
)
def signup(
    payload: SignupRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> SignupResponse:
    """
    1. Validate the request schema (Pydantic handles this).
    2. Reject duplicate email addresses with 409.
    3. Hash the password and persist User + LocalAuth rows.
    4. Schedule the verification email as a BackgroundTask so the response
       is returned immediately without waiting for the Resend API.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        # Recovery path: allow re-signup for accounts that exist but are still
        # unverified. This avoids dead-ends when a previous verification email
        # was never delivered.
        if existing.is_verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists.",
            )

        local_auth = (
            db.query(LocalAuth)
            .filter(LocalAuth.user_id == existing.user_id)
            .first()
        )
        if not local_auth:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This email is already linked to another authentication method. "
                    "Please use Google sign-in."
                ),
            )

        token = generate_verification_token(payload.email)
        token_expires = datetime.now(timezone.utc) + timedelta(hours=24)

        # Refresh profile and credentials so the most recent signup form values
        # become the source of truth before verification.
        existing.first_name = payload.first_name
        existing.middle_name = payload.middle_name
        existing.last_name = payload.last_name
        existing.gender = payload.gender.value if payload.gender else None
        existing.date_of_birth = payload.date_of_birth

        local_auth.password_hash = hash_password(payload.password)
        local_auth.verification_token = token
        local_auth.token_expires_at = token_expires
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists.",
            )

        background_tasks.add_task(
            _send_verification_email_safe,
            to_email=payload.email,
            token=token,
            first_name=payload.first_name,
            base_url=BACKEND_BASE_URL,
        )

        return SignupResponse(
            user_id=existing.user_id,
            email=payload.email,
            message=(
                "Your account already exists but is not verified yet. "
                "We have sent a new verification email."
            ),
        )

    user_id = str(uuid.uuid4())
    user = User(
        user_id=user_id,
        first_name=payload.first_name,
        middle_name=payload.middle_name,
        last_name=payload.last_name,
        email=payload.email,
        gender=payload.gender.value if payload.gender else None,
        date_of_birth=payload.date_of_birth,
        is_verified=False,
    )
    db.add(user)
    db.flush()  # write the User row before the FK-constrained LocalAuth row

    token = generate_verification_token(payload.email)
    token_expires = datetime.now(timezone.utc) + timedelta(hours=24)

    local_auth = LocalAuth(
        user_id=user_id,
        password_hash=hash_password(payload.password),
        verification_token=token,
        token_expires_at=token_expires,
    )
    db.add(local_auth)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    background_tasks.add_task(
        _send_verification_email_safe,
        to_email=payload.email,
        token=token,
        first_name=payload.first_name,
        base_url=BACKEND_BASE_URL,
    )

    return SignupResponse(
        user_id=user_id,
        email=payload.email,
        message=(
            "Account created successfully. "
            "Please check your inbox to verify your email address."
        ),
    )


# ===========================================================================
# POST /login
# ===========================================================================


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate using email and password",
)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Local login flow:
      1. Find the user by email.
      2. Verify the supplied password against LocalAuth.password_hash.
      3. Require email verification before issuing an access token.
      4. Return a signed JWT plus basic user identity fields.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    local_auth = db.query(LocalAuth).filter(LocalAuth.user_id == user.user_id).first()
    if not local_auth or not local_auth.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(payload.password, local_auth.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before logging in.",
        )

    access_token = create_access_token({"sub": user.user_id, "email": user.email})
    _set_auth_cookie(response, access_token)
    return TokenResponse(
        access_token=access_token,
        user_id=user.user_id,
        email=user.email,
    )


@router.post(
    "/logout",
    summary="Logout current user session",
)
def logout(response: Response):
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    return {"message": "Logged out successfully."}


@router.get(
    "/me",
    summary="Return currently authenticated user profile",
)
def me(current_user: User = Depends(get_current_user)):
    # Query is strictly user_id-scoped via get_current_user().
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "is_verified": current_user.is_verified,
    }


# ===========================================================================
# GET /verify-email
# ===========================================================================


@router.get(
    "/verify-email",
    summary="Verify a user's email address using the signed token",
)
def verify_email(token: str, db: Session = Depends(get_db)):
    """
    1. Decode and validate the itsdangerous token (checks signature + expiry).
    2. Look up the user and their LocalAuth record.
    3. Compare the stored token to prevent replay (single-use enforcement).
    4. Mark the user as verified and clear the stored token.
    """
    def _redirect_result(status_value: str, message_value: str):
        return RedirectResponse(
            url=_build_frontend_redirect(
                FRONTEND_VERIFY_EMAIL_PATH,
                params={"status": status_value, "message": message_value},
            ),
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    try:
        email = decode_verification_token(token)
    except SignatureExpired:
        return _redirect_result(
            "error",
            "This verification link has expired. Please request a new one.",
        )
    except BadSignature:
        return _redirect_result(
            "error",
            "Invalid verification token.",
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return _redirect_result(
            "error",
            "No account found for this verification link.",
        )

    local_auth = db.query(LocalAuth).filter(LocalAuth.user_id == user.user_id).first()
    if not local_auth or local_auth.verification_token != token:
        return _redirect_result(
            "error",
            "This verification link has already been used or is invalid.",
        )

    user.is_verified = True
    local_auth.verification_token = None
    local_auth.token_expires_at = None
    db.commit()

    return _redirect_result(
        "success",
        "Email verified successfully. You can now log in.",
    )


# ===========================================================================
# GET /google/login
# ===========================================================================


@router.get(
    "/google/login",
    summary="Redirect the browser to Google's OAuth 2.0 authorization page",
)
def google_login():
    """
    Build and return a 307 redirect to Google's authorization endpoint.
    The frontend opens this URL (or redirects to it) to start the OAuth flow.
    """
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    return RedirectResponse(
        url=f"{_GOOGLE_AUTH_URL}?{urlencode(params)}",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )


# ===========================================================================
# GET /google/callback
# ===========================================================================


@router.get(
    "/google/callback",
    summary="Handle Google OAuth callback and redirect to frontend",
)
def google_callback(code: str, db: Session = Depends(get_db)):
    """
    OAuth callback flow:
      1. Exchange the authorization code for a Google access token.
      2. Fetch the authenticated user's profile from Google's userinfo endpoint.
      3. Look up an existing OAuthAccount by (provider_type, provider_id).
         a. Found  → update the stored access token, return JWT.
         b. Not found, but email matches a local user → link the Google account.
         c. Completely new → create User + OAuthAccount, return JWT.
    """
    # Step 1: exchange the authorization code for tokens
    try:
        with httpx.Client(timeout=10.0) as http:
            token_response = http.post(
                _GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google token exchange failed due to a network error.",
        )

    if token_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code with Google.",
        )

    google_access_token: str = token_response.json().get("access_token", "")

    # Step 2: fetch user info
    try:
        with httpx.Client(timeout=10.0) as http:
            userinfo_response = http.get(
                _GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {google_access_token}"},
            )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to retrieve user information from Google.",
        )

    if userinfo_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to retrieve user information from Google.",
        )

    userinfo: dict = userinfo_response.json()
    google_sub: str = userinfo.get("sub", "")
    google_email: str = userinfo.get("email", "")
    google_first_name: str = userinfo.get("given_name") or "User"
    google_last_name: str = userinfo.get("family_name") or google_first_name
    if not google_sub or not google_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google user information is incomplete.",
        )

    # Step 3: resolve the user record
    oauth_account = (
        db.query(OAuthAccount)
        .filter(
            OAuthAccount.provider_type == "google",
            OAuthAccount.provider_id == google_sub,
        )
        .first()
    )

    if oauth_account:
        # Known OAuth account — refresh the stored access token
        oauth_account.access_token = google_access_token
        db.commit()
        user = db.query(User).filter(User.user_id == oauth_account.user_id).first()

    else:
        # Check if this email already has a local (password) account
        user = db.query(User).filter(User.email == google_email).first()

        if user:
            # Link the Google identity to the existing local account
            new_oauth = OAuthAccount(
                id=str(uuid.uuid4()),
                user_id=user.user_id,
                provider_type="google",
                provider_id=google_sub,
                access_token=google_access_token,
            )
            db.add(new_oauth)
            try:
                db.commit()
            except IntegrityError:
                # Concurrent link attempt may have won the race; continue safely.
                db.rollback()

        else:
            # Brand-new user arriving via Google — auto-verified
            user_id = str(uuid.uuid4())
            user = User(
                user_id=user_id,
                first_name=google_first_name,
                last_name=google_last_name,
                email=google_email,
                is_verified=True,
            )
            db.add(user)
            db.flush()

            new_oauth = OAuthAccount(
                id=str(uuid.uuid4()),
                user_id=user_id,
                provider_type="google",
                provider_id=google_sub,
                access_token=google_access_token,
            )
            db.add(new_oauth)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                oauth_account = (
                    db.query(OAuthAccount)
                    .filter(
                        OAuthAccount.provider_type == "google",
                        OAuthAccount.provider_id == google_sub,
                    )
                    .first()
                )
                if not oauth_account:
                    raise
                user = db.query(User).filter(User.user_id == oauth_account.user_id).first()

    access_token = create_access_token({"sub": user.user_id, "email": user.email})
    redirect_url = _build_frontend_redirect(FRONTEND_DASHBOARD_PATH)
    redirect_response = RedirectResponse(url=redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    _set_auth_cookie(redirect_response, access_token)
    return redirect_response
