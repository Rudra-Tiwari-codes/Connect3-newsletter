"""
Python port of scripts/embed-events.ts.
Reads all_posts.json, embeds/classifies each post, and upserts to Supabase.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict

from python_app.embeddings import embed_event
from python_app.supabase_client import supabase


POSTS_PATH = Path(__file__).resolve().parents[1] / "all_posts.json"


def extract_title(caption: str) -> str:
  lines = [ln.strip() for ln in caption.split("\n") if ln.strip()]
  if not lines:
    return "Event"
  title = lines[0][:200]
  return title or "Event"


def extract_location(caption: str) -> str | None:
  patterns = [
    "Location:",
    "Where:",
    "location:",
    "where:",
  ]
  for line in caption.split("\n"):
    for pat in patterns:
      if pat in line:
        return line.split(pat, 1)[1].strip()
  return None


def upsert_event(post: Dict[str, Any], category: str | None) -> None:
  supabase.table("events").upsert(
    {
      "id": post["id"],
      "title": extract_title(post.get("caption", "")),
      "description": post.get("caption"),
      "event_date": post.get("timestamp"),
      "location": extract_location(post.get("caption", "")),
      "category": category,
      "source_url": post.get("permalink"),
    },
    on_conflict="id",
  ).execute()


def upsert_embedding(record: Dict[str, Any]) -> None:
  supabase.table("event_embeddings").upsert(
    {
      "event_id": record["event_id"],
      "embedding": record["embedding"],
      "category": record["category"],
      "created_at": record["created_at"],
    },
    on_conflict="event_id",
  ).execute()


def main() -> None:
  if not POSTS_PATH.exists():
    raise SystemExit(f"all_posts.json not found at {POSTS_PATH}")

  posts = json.loads(POSTS_PATH.read_text())
  total = len(posts)
  print(f"Found {total} posts to process")

  success = 0
  errors = 0
  batch_size = 5

  for idx, post in enumerate(posts, 1):
    print(f"[{idx}/{total}] {post.get('id')}")
    try:
      record = embed_event(post)
      upsert_event(post, record["category"])
      upsert_embedding(record)
      success += 1
    except Exception as exc:
      errors += 1
      print(f"  Error: {exc}")

    # Light rate limiting every batch
    if idx % batch_size == 0:
      time.sleep(1.0)

  print("=" * 40)
  print(f"Embedding complete. Success: {success}, Errors: {errors}")


if __name__ == "__main__":
  main()
