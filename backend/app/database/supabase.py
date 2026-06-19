"""Supabase client factories for user-scoped and service-role access."""

from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from app.config import settings

_service_role_client: Client | None = None


def create_user_client(access_token: str) -> Client:
    """Client that acts as the authenticated user (RLS applies)."""
    return create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
        options=SyncClientOptions(
            headers={"Authorization": f"Bearer {access_token}"},
            auto_refresh_token=False,
            persist_session=False,
        ),
    )


def get_service_role_client() -> Client:
    """Privileged backend client (bypasses RLS). Reused across requests."""
    global _service_role_client
    if _service_role_client is None:
        _service_role_client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
            options=SyncClientOptions(
                auto_refresh_token=False,
                persist_session=False,
            ),
        )
    return _service_role_client
