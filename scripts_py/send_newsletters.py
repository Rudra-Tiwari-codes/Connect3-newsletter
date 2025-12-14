"""
Python port of scripts/send-newsletters.ts.
Ranks events for each user and sends emails via Gmail SMTP.
"""

from python_app.scoring import rank_events_for_user
from python_app.email_sender import send_personalized_email
from python_app.supabase_client import supabase


def main() -> None:
  print("Starting newsletter generation and delivery...")
  users_resp = supabase.table("users").select("*").execute()
  users = users_resp.data or []
  print(f"Found {len(users)} users")

  for user in users:
    try:
      ranked = rank_events_for_user(user["id"], limit=10)
      if not ranked:
        print(f"Skipping {user.get('email')}: no events")
        continue
      send_personalized_email(user, ranked)
      print(f"✓ Sent to {user.get('email')}")
    except Exception as exc:
      print(f"Failed for {user.get('email')}: {exc}")

  print("Newsletter delivery complete.")


if __name__ == "__main__":
  main()
