"""
Embedding and classification helpers (Python port of src/lib/embeddings.ts).
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from openai import OpenAI

from .config import require_env
from .supabase_client import supabase

OPENAI_API_KEY = require_env("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Event categories for Connect3
CONNECT3_CATEGORIES = [
  "tech_workshop",
  "career_networking",
  "hackathon",
  "social_event",
  "academic_revision",
  "recruitment",
  "industry_talk",
  "sports_recreation",
  "entrepreneurship",
  "community_service",
]

EMBEDDING_DIM = 1536


def _prepare_event_text(caption: str) -> str:
  """Clean caption text for embedding."""
  clean = re.sub(r"#(\w+)", r"\1", caption or "")
  # Strip common emoji ranges
  emoji_ranges = [
    r"\U0001F600-\U0001F64F",
    r"\U0001F300-\U0001F5FF",
    r"\U0001F680-\U0001F6FF",
    r"\U0001F1E0-\U0001F1FF",
    r"\u2600-\u26FF",
    r"\u2700-\u27BF",
  ]
  clean = re.sub(f"[{''.join(emoji_ranges)}]", "", clean)
  clean = re.sub(r"\s+", " ", clean).strip()
  return clean[:8000]


def generate_embedding(text: str) -> List[float]:
  resp = client.embeddings.create(
    model="text-embedding-3-small",
    input=text,
    encoding_format="float",
  )
  return resp.data[0].embedding  # type: ignore[return-value]


def classify_event_category(caption: str) -> Optional[str]:
  prompt = f"Classify this university club event into ONE of these categories: {', '.join(CONNECT3_CATEGORIES)}. Respond with only the category name."
  try:
    resp = client.chat.completions.create(
      model="gpt-4o-mini",
      messages=[
        {"role": "system", "content": prompt},
        {"role": "user", "content": caption[:2000]},
      ],
      temperature=0.1,
      max_tokens=50,
    )
    category = (resp.choices[0].message.content or "").strip().lower()
    return category if category in CONNECT3_CATEGORIES else None
  except Exception as exc:  # pragma: no cover - defensive logging
    print(f"Error classifying event: {exc}")
    return None


def embed_event(post: Dict[str, Any]) -> Dict[str, Any]:
  """
  Build an event embedding record from an Instagram-like post dict.
  Expected keys: id, caption, timestamp.
  """
  caption = post.get("caption", "")
  clean_text = _prepare_event_text(caption)
  embedding = generate_embedding(clean_text)
  category = classify_event_category(caption)

  return {
    "event_id": post["id"],
    "embedding": embedding,
    "category": category,
    "created_at": post.get("timestamp") or datetime.utcnow().isoformat(),
  }


def embed_user(user_id: str) -> List[float]:
  """
  Compute a user embedding from interactions; falls back to preferences.
  Mirrors the TypeScript logic with weighted averaging.
  """
  interactions = supabase.table("feedback_logs").select("event_id, action").eq("user_id", user_id).execute().data or []
  if interactions:
    weights = {"like": 1.0, "click": 0.5, "dislike": -0.5}
    event_ids = [i["event_id"] for i in interactions]
    embs = supabase.table("event_embeddings").select("event_id, embedding").in_("event_id", event_ids).execute().data or []
    vec = [0.0] * EMBEDDING_DIM
    total = 0.0
    for i in interactions:
      emb_row = next((e for e in embs if e["event_id"] == i["event_id"]), None)
      if not emb_row:
        continue
      weight = weights.get(i.get("action"), 0.0)
      emb_vec = emb_row["embedding"]
      for idx, val in enumerate(emb_vec):
        vec[idx] += val * weight
      total += abs(weight)
    return [v / total for v in vec] if total else vec

  # Cold start: preferences text
  resp = supabase.table("user_preferences").select("*").eq("user_id", user_id).limit(1).execute()
  prefs = resp.data[0] if resp.data else None
  if prefs:
    interests = [k for k, v in prefs.items() if isinstance(v, (int, float)) and v > 0.6]
    pref_text = f"University student interested in: {', '.join(interests) or 'general university events'}"
  else:
    pref_text = "University student interested in general university events"
  return generate_embedding(pref_text)
