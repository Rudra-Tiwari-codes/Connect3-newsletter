"""
Python port of scripts/ingest-events.ts.
Classifies uncategorized events and updates Supabase.
"""

from python_app.embeddings import classify_event_category
from python_app.supabase_client import supabase


def main() -> None:
  print("Starting event ingestion and classification...")
  resp = supabase.table("events").select("*").is_("category", None).execute()
  events = resp.data or []

  if not events:
    print("No unclassified events found.")
    return

  print(f"Found {len(events)} unclassified events")
  success = 0

  for event in events:
    category = classify_event_category(event.get("description") or event.get("title") or "")
    if not category:
      print(f"Skipping event {event.get('id')}: could not classify")
      continue
    update_resp = supabase.table("events").update({"category": category}).eq("id", event["id"]).execute()
    if update_resp.data is not None:
      success += 1
    else:
      print(f"Failed to update event {event.get('id')}")

  print(f"✓ Successfully classified {success} events")


if __name__ == "__main__":
  main()
