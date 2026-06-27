"""revoke public execute on rls_auto_enable

Revision ID: b2f1c7a9d4e0
Revises: 1ddb06794f48
Create Date: 2026-06-27 01:20:00.000000

Hardening: ``public.rls_auto_enable()`` is a SECURITY DEFINER event-trigger
helper. PostgREST exposes any ``public`` function with EXECUTE granted to
``anon`` / ``authenticated`` as an RPC endpoint, so revoke those grants to keep
it off the public API surface. The event trigger still fires (it runs as its
owner, not via an EXECUTE grant). Guarded so it is a no-op where the function
does not exist.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "b2f1c7a9d4e0"
down_revision: Union[str, Sequence[str], None] = "1ddb06794f48"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'public' AND p.proname = 'rls_auto_enable'
            ) THEN
                REVOKE EXECUTE ON FUNCTION public.rls_auto_enable()
                    FROM PUBLIC, anon, authenticated;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = 'public' AND p.proname = 'rls_auto_enable'
            ) THEN
                GRANT EXECUTE ON FUNCTION public.rls_auto_enable() TO PUBLIC;
            END IF;
        END $$;
        """
    )
