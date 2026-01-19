"""Ingest events, generate embeddings, and classify uncategorized events in Supabase."""

import sys
from pathlib import Path
from typing import Iterable, Optional

# Add parent directory to path so we can import python_app from any directory
ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

from categorize_events import EventClassifier
from python_app.supabase_client import ensure_ok, supabase
import embed_events
import populate_events


DEFAULT_SIMULATED_POSTS = ROOT_DIR / "all_posts_simulated.json"
DEFAULT_POSTS = ROOT_DIR / "all_posts.json"


def resolve_posts_path(posts_arg: Optional[Path]) -> Path:
  if posts_arg:
    return posts_arg.expanduser()
  if DEFAULT_SIMULATED_POSTS.exists():
    return DEFAULT_SIMULATED_POSTS
  return DEFAULT_POSTS


def _stringify_ids(values: Iterable[object]) -> set:
  return {str(value) for value in values if value is not None}


def verify_status() -> None:
  events_resp = supabase.table("events").select("id, category").execute()
  ensure_ok(events_resp, action="select events for verification")
  events = events_resp.data or []

  event_ids = _stringify_ids([event.get("id") for event in events])
  uncategorized = [event for event in events if not event.get("category")]

  embeddings_resp = supabase.table("event_embeddings").select("event_id").execute()
  ensure_ok(embeddings_resp, action="select event_embeddings for verification")
  embedding_ids = _stringify_ids([row.get("event_id") for row in (embeddings_resp.data or [])])

  missing_embeddings = sorted(event_ids - embedding_ids)

  print("\nVerification summary:")
  print(f"  Events in table: {len(event_ids)}")
  print(f"  Events missing category: {len(uncategorized)}")
  print(f"  Embeddings in table: {len(embedding_ids)}")
  print(f"  Events missing embeddings: {len(missing_embeddings)}")
  if missing_embeddings:
    sample = ", ".join(missing_embeddings[:10])
    print(f"  Sample missing embeddings: {sample}")


def main(
  posts_path: Optional[Path] = None,
  populate: bool = False,
  embed: bool = False,
  verify: bool = False,
  start_batch: int = 1,
) -> None:
  print("Starting event ingestion and classification...")
  try:
    resolved_posts = resolve_posts_path(posts_path)
    if embed:
      print(f"Embedding events from {resolved_posts}...")
      embed_events.main(start_batch=start_batch, posts_path=resolved_posts)
    if populate:
      print(f"Upserting events from {resolved_posts}...")
      populate_events.main(posts_path=resolved_posts)

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
    if verify:
      verify_status()
  except Exception as exc:
    print(f"Error during ingestion: {exc}")
    raise SystemExit(1)


if __name__ == "__main__":
  import argparse

  parser = argparse.ArgumentParser()
  parser.add_argument("--populate", action="store_true", help="Upsert events from posts JSON")
  parser.add_argument("--embed", action="store_true", help="Generate embeddings from posts JSON")
  parser.add_argument("--verify", action="store_true", help="Verify embeddings and categories")
  parser.add_argument("--posts", type=Path, help="Path to posts JSON")
  parser.add_argument("--start-batch", type=int, default=1, help="Batch number for embeddings")
  args = parser.parse_args()

  main(
    posts_path=args.posts,
    populate=args.populate,
    embed=args.embed,
    verify=args.verify,
    start_batch=args.start_batch,
  )
