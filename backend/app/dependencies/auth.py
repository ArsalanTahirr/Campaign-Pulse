"""
dependencies/auth.py — Authenticated-user FastAPI dependency.

get_current_user reads the JWT access_token cookie, decodes it, and returns
the corresponding User ORM object.  Raises HTTP 401 if the token is missing,
expired, or invalid, and HTTP 404 if the user_id in the token no longer exists.
"""

from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session
from typing import Optional

from app.auth import decode_access_token
from app.database import get_db
from app.models import User


def get_current_user(
    access_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency — resolves the Bearer user from the access_token cookie.

    Usage:
        @router.get("/me")
        def me(user: User = Depends(get_current_user)):
            ...
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(access_token)
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload.",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is expired or invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return user
