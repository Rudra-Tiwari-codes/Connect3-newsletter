"""Helpers for accessing newsletter_subscribers data."""

from typing import Dict, Iterable, Optional

from .logger import get_logger
from .supabase_client import supabase

logger = get_logger(__name__)


def _try_select_email(
    column: str,
    user_ids: Iterable[str],
) -> Optional[Dict[str, str]]:
    try:
        resp = (
            supabase.table("newsletter_subscribers")
            .select(f"{column},email")
            .in_(column, list(user_ids))
            .execute()
        )
    except Exception as exc:
        logger.debug(f"newsletter_subscribers select failed for column {column}: {exc}")
        return None

    emails: Dict[str, str] = {}
    for row in resp.data or []:
        key = row.get(column)
        email = row.get("email")
        if key and email:
            emails[str(key)] = email
    return emails


def fetch_subscriber_emails(user_ids: Iterable[str]) -> Dict[str, str]:
    """Fetch subscriber emails keyed by user id."""
    user_ids = [uid for uid in user_ids if uid]
    if not user_ids:
        return {}

    for column in ("user_id", "profile_id", "id"):
        emails = _try_select_email(column, user_ids)
        if emails is not None:
            return emails

    logger.warning("Failed to fetch subscriber emails from newsletter_subscribers.")
    return {}


def fetch_subscriber_email(user_id: str) -> Optional[str]:
    """Fetch a single subscriber email by user id."""
    if not user_id:
        return None

    for column in ("user_id", "profile_id", "id"):
        try:
            resp = (
                supabase.table("newsletter_subscribers")
                .select("email")
                .eq(column, user_id)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            logger.debug(f"newsletter_subscribers lookup failed for column {column}: {exc}")
            continue

        row = (resp.data or [None])[0]
        if row and row.get("email"):
            return row.get("email")

    logger.warning("Failed to fetch subscriber email from newsletter_subscribers.")
    return None
