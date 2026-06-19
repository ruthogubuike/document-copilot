"""FastAPI dependencies for Supabase JWT authentication."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase_auth.errors import AuthError

from app.database.supabase import create_user_client

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Verified Supabase Auth user attached to a request."""

    id: uuid.UUID
    email: str


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    token = credentials.credentials.strip()
    if not token:
        raise _unauthorized()
    return token


def get_current_user(token: str = Depends(get_bearer_token)) -> AuthenticatedUser:
    client = create_user_client(token)
    try:
        response = client.auth.get_user(token)
    except AuthError:
        raise _unauthorized("Invalid or expired token") from None

    if response is None or not response.user.email:
        raise _unauthorized("Invalid or expired token")

    return AuthenticatedUser(
        id=uuid.UUID(response.user.id),
        email=response.user.email,
    )


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
