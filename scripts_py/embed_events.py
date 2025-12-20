"""Embed and classify events from all_posts.json, then upsert embeddings to Supabase."""

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict

# Add parent directory to path so we can import python_app
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python_app.embeddings import embed_event
from python_app.supabase_client import ensure_ok, supabase


POSTS_PATH = Path(__file__).resolve().parents[1] / "all_posts.json"


def upsert_embedding(record: Dict[str, Any]) -> None:
  resp = supabase.table("event_embeddings").upsert(
    {
      "event_id": record["event_id"],
      "embedding": record["embedding"],
      "category": record["category"],
      "created_at": record["created_at"],
    },
    on_conflict="event_id",
  ).execute()
  ensure_ok(resp, action="upsert event_embeddings")


def print_category_distribution() -> None:
  resp = supabase.table("event_embeddings").select("category").execute()
  ensure_ok(resp, action="select event_embeddings")
  rows = resp.data or []
  if not rows:
    return

  counts: Dict[str, int] = {}
  for row in rows:
    cat = row.get("category") or "uncategorized"
    counts[cat] = counts.get(cat, 0) + 1

  print("\nCategory Distribution:")
  for category, count in sorted(counts.items(), key=lambda item: item[1], reverse=True):
    bar = "#" * ((count + 1) // 2)
    print(f"  {category.ljust(20)} {str(count).rjust(3)} {bar}")


def main() -> None:
  if not POSTS_PATH.exists():
    raise SystemExit(f"all_posts.json not found at {POSTS_PATH}")

  print("Starting event embedding process...\n")
  posts = json.loads(POSTS_PATH.read_text())
  total = len(posts)
  print(f"Found {total} posts to process\n")

  success = 0
  errors = 0
  batch_size = 5
  total_batches = (total + batch_size - 1) // batch_size

  for batch_start in range(0, total, batch_size):
    batch = posts[batch_start: batch_start + batch_size]
    batch_idx = (batch_start // batch_size) + 1
    print(f"Processing batch {batch_idx}/{total_batches}...")

    for post in batch:
      try:
        record = embed_event(post)
        upsert_embedding(record)
        success += 1
        print(f"  ✓ Embedded: {post.get('id')} -> {record.get('category') or 'uncategorized'}")
      except Exception as exc:
        errors += 1
        print(f"  ✗ Error: {exc}")

    if batch_start + batch_size < total:
      time.sleep(1.0)

  print("=" * 40)
  print(f"Embedding complete. Success: {success}, Errors: {errors}")
  print_category_distribution()


if __name__ == "__main__":
  main()
