"""Rank events for each user and send personalized newsletters via Gmail SMTP."""

from python_app.email_sender import EmailDeliveryService
from python_app.recommender import TwoTowerRecommender
from python_app.supabase_client import ensure_ok, supabase


def main() -> None:
  print("Starting newsletter generation and delivery...")
  try:
    users_resp = supabase.table("users").select("*").execute()
    ensure_ok(users_resp, action="select users")
    users = users_resp.data or []
    print(f"Found {len(users)} users")

    # Use Two-Tower recommender for semantic embedding-based recommendations
    recommender = TwoTowerRecommender()
    print("Loading event embeddings into vector index...")
    event_count = recommender.load_event_index()
    print(f"Loaded {event_count} events into recommendation engine")

    email_service = EmailDeliveryService()
    ranked_events_by_user: dict[str, list[dict]] = {}

    for user in users:
      try:
        recommendations = recommender.get_recommendations(user["id"])
        if recommendations:
          ranked_events_by_user[user["id"]] = recommendations
          print(f"  Generated {len(recommendations)} recommendations for user {user.get('email', user['id'])}")
      except Exception as exc:
        print(f"Failed to get recommendations for user {user.get('id')}: {exc}")

    print(f"Generated recommendations for {len(ranked_events_by_user)} users")
    
    if ranked_events_by_user:
      email_service.send_newsletters(ranked_events_by_user)
    else:
      print("No recommendations generated - skipping email delivery")
    
    print("Newsletter delivery complete!")
  except Exception as exc:
    print(f"Error during newsletter sending: {exc}")
    raise SystemExit(1)


if __name__ == "__main__":
  main()
