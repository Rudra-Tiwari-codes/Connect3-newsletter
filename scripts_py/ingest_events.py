"""Classify uncategorized events in Supabase using OpenAI."""

from categorize_events import EventClassifier
from python_app.supabase_client import ensure_ok, supabase


def main() -> None:
  print("Starting event ingestion and classification...")
  try:
    resp = supabase.table("events").select("*").is_("category", None).execute()
    ensure_ok(resp, action="select events")
    events = resp.data or []

    if not events:
      print("No unclassified events found.")
      return

    print(f"Found {len(events)} unclassified events")
    classifier = EventClassifier()
    classifications = classifier.classify_batch(events)

    success = 0
    for event_id, category in classifications.items():
      update_resp = supabase.table("events").update({"category": category}).eq("id", event_id).execute()
      try:
        ensure_ok(update_resp, action="update events")
        success += 1
      except Exception:
        print(f"Failed to update event {event_id}")

    print(f"✓ Successfully classified {success} events")
  except Exception as exc:
    print(f"Error during ingestion: {exc}")
    raise SystemExit(1)


if __name__ == "__main__":
  main()
