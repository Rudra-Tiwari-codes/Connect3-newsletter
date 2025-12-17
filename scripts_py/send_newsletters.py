"""Rank events for each user and send personalized newsletters via Gmail SMTP."""

from python_app.email_sender import EmailDeliveryService
from python_app.scoring import EventScoringService
from python_app.supabase_client import ensure_ok, supabase

def main() -> None:
  print("Starting newsletter generation and delivery...")
  try:
    users_resp = supabase.table("users").select("*").execute()
    ensure_ok(users_resp, action="select users")
    users = users_resp.data or []
    print(f"Found {len(users)} users")

    scoring_service = EventScoringService()
    email_service = EmailDeliveryService()
    ranked_events_by_user: dict[str, list[dict]] = {}

    for user in users:
      try:
        ranked = scoring_service.rank_events_for_user(user["id"], limit=10)
        if ranked:
          ranked_events_by_user[user["id"]] = ranked
      except Exception as exc:
        print(f"Failed to rank events for user {user.get('id')}: {exc}")

    print(f"Ranked events for {len(ranked_events_by_user)} users")
    email_service.send_newsletters(ranked_events_by_user)
    print("✓ Newsletter delivery complete!")
  except Exception as exc:
    print(f"Error during newsletter sending: {exc}")
    raise SystemExit(1)


if __name__ == "__main__":
  main()
