"""Helpers for accessing Supabase auth.users data via the Admin API."""

from typing import Dict, List, Optional

from .logger import get_logger
from .supabase_client import supabase

logger = get_logger(__name__)


def _auth_admin():
    """Return the Supabase Auth Admin client if available."""
    auth = getattr(supabase, "auth", None)
    return getattr(auth, "admin", None) if auth else None


def fetch_auth_emails(user_ids: List[str]) -> Dict[str, str]:
    """Batch fetch auth emails keyed by user id."""
    if not user_ids:
        return {}

    admin = _auth_admin()
    if not admin:
        logger.warning("Supabase auth admin client not available; cannot fetch auth emails.")
        return {}

    emails: Dict[str, str] = {}
    for user_id in user_ids:
        if not user_id:
            continue
        try:
            resp = admin.get_user_by_id(user_id)
        except Exception as exc:
            logger.warning(f"Failed to fetch auth email for user {user_id}: {exc}")
            continue
        user = getattr(resp, "user", None)
        if user is None and isinstance(resp, dict):
            user = resp.get("user")
        if not user:
            continue
        email = getattr(user, "email", None) if not isinstance(user, dict) else user.get("email")
        if email:
            emails[str(user_id)] = email
    return emails


def fetch_auth_email(user_id: str) -> Optional[str]:
    """Fetch a single auth email by user id."""
    if not user_id:
        return None

    admin = _auth_admin()
    if not admin:
        logger.warning("Supabase auth admin client not available; cannot fetch auth email.")
        return None

    try:
        resp = admin.get_user_by_id(user_id)
    except Exception as exc:
        logger.warning(f"Failed to fetch auth email for user {user_id}: {exc}")
        return None

    user = getattr(resp, "user", None)
    if user is None and isinstance(resp, dict):
        user = resp.get("user")
    if not user:
        return None
    return getattr(user, "email", None) if not isinstance(user, dict) else user.get("email")
