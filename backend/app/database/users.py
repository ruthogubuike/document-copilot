"""User profile persistence in public.users."""

from __future__ import annotations

from app.auth.dependencies import AuthenticatedUser
from app.database.supabase import get_service_role_client


def ensure_user(user: AuthenticatedUser) -> None:
    """Ensure a public.users row exists for the authenticated Supabase user."""
    client = get_service_role_client()
    client.table("users").upsert(
        {"id": str(user.id), "email": user.email},
        on_conflict="id",
    ).execute()
