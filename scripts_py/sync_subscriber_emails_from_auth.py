"""Sync subscriber emails from Supabase auth users by profile_id."""

import argparse
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python_app.logger import get_logger, setup_logging
from python_app.supabase_client import ensure_ok, supabase

logger = get_logger(__name__)


def _get_admin():
    auth = getattr(supabase, "auth", None)
    return getattr(auth, "admin", None) if auth else None


def _extract_email(resp: Any) -> Optional[str]:
    user = getattr(resp, "user", None)
    if user is None and isinstance(resp, dict):
        user = resp.get("user")
    if not user:
        return None
    if isinstance(user, dict):
        return user.get("email")
    return getattr(user, "email", None)


def main() -> None:
    setup_logging()

    parser = argparse.ArgumentParser(description="Sync subscriber emails from auth.users.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing subscriber emails.")
    parser.add_argument("--dry-run", action="store_true", help="Log updates without writing to Supabase.")
    args = parser.parse_args()

    admin = _get_admin()
    if not admin:
        raise RuntimeError("Supabase auth admin client not available. Ensure SUPABASE_SERVICE_KEY is set.")

    resp = supabase.table("subscribers").select("id,profile_id,email").execute()
    ensure_ok(resp, action="select subscribers")
    rows = resp.data or []

    total = 0
    updated = 0
    skipped = 0
    missing = 0

    for row in rows:
        profile_id = row.get("profile_id")
        if not profile_id:
            skipped += 1
            continue

        total += 1
        current_email = row.get("email")
        if current_email and not args.overwrite:
            skipped += 1
            continue

        try:
            auth_resp = admin.get_user_by_id(profile_id)
        except Exception as exc:
            logger.warning(f"Failed to fetch auth user {profile_id}: {exc}")
            missing += 1
            continue

        email = _extract_email(auth_resp)
        if not email:
            missing += 1
            continue

        if args.dry_run:
            logger.info(f"[dry-run] Would set subscriber {row.get('id')} email to {email}")
            updated += 1
            continue

        update_resp = (
            supabase.table("subscribers")
            .update({"email": email})
            .eq("id", row.get("id"))
            .execute()
        )
        ensure_ok(update_resp, action="update subscriber email")
        updated += 1

    logger.info(
        "Email sync complete: %s total profile-linked, %s updated, %s skipped, %s missing",
        total,
        updated,
        skipped,
        missing,
    )


if __name__ == "__main__":
    main()
