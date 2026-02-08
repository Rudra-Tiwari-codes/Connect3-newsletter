"""Helpers for accessing Supabase auth.users data."""

from typing import Dict, List, Optional

from .logger import get_logger
from .supabase_client import ensure_ok, supabase

logger = get_logger(__name__)


def _auth_users_table():
    """Return a query builder for auth.users, compatible across supabase-py versions."""
    schema_fn = getattr(supabase, "schema", None)
    if callable(schema_fn):
        return supabase.schema("auth").table("users")
    return supabase.table("auth.users")


def fetch_auth_emails(user_ids: List[str]) -> Dict[str, str]:
    """Batch fetch auth emails keyed by user id."""
    if not user_ids:
        return {}

    try:
        resp = _auth_users_table().select("id,email").in_("id", user_ids).execute()
        ensure_ok(resp, action="select auth.users emails")
    except Exception as exc:
        logger.warning(f"Failed to fetch auth emails: {exc}")
        return {}

    emails: Dict[str, str] = {}
    for row in resp.data or []:
        user_id = row.get("id")
        email = row.get("email")
        if user_id and email:
            emails[str(user_id)] = email
    return emails


def fetch_auth_email(user_id: str) -> Optional[str]:
    """Fetch a single auth email by user id."""
    if not user_id:
        return None

    try:
        resp = _auth_users_table().select("email").eq("id", user_id).limit(1).execute()
        ensure_ok(resp, action="select auth.users email")
    except Exception as exc:
        logger.warning(f"Failed to fetch auth email for user {user_id}: {exc}")
        return None

    row = (resp.data or [None])[0]
    if not row:
        return None
    return row.get("email")
