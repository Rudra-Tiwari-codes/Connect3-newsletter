"""Embedding and classification helpers for Connect3 (Python-first implementation)."""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .logger import get_logger
from .openai_client import client, with_retry
from .supabase_client import ensure_ok, supabase

logger = get_logger(__name__)

# Event categories for Connect3 - standardized across all modules
CONNECT3_CATEGORIES = [
  "academic_workshops",
  "career_networking",
  "social_cultural",
  "sports_fitness",
  "arts_music",
  "tech_innovation",
  "volunteering_community",
  "food_dining",
  "travel_adventure",
  "health_wellness",
  "entrepreneurship",
  "environment_sustainability",
  "gaming_esports",
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


def _parse_embedding(raw: Any) -> Optional[List[float]]:
  if isinstance(raw, list):
    return raw
  if isinstance(raw, str):
    try:
      parsed = json.loads(raw)
      if isinstance(parsed, list):
        return parsed
    except Exception:
      return None
  return None


def generate_embedding(text: str) -> List[float]:
  if not text:
    return [0.0] * EMBEDDING_DIM

  def _call():
    return client.embeddings.create(
      model="text-embedding-3-small",
      input=text,
      encoding_format="float",
    )

  resp = with_retry(_call, label="OpenAI embedding")
  return resp.data[0].embedding  # type: ignore[return-value]


def classify_event_category(caption: str) -> Optional[str]:
  if not caption:
    return None

  prompt = (
    "Classify this university club event into ONE of these categories: "
    f"{', '.join(CONNECT3_CATEGORIES)}. Respond with only the category name."
  )
  try:
    def _call():
      return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
          {"role": "system", "content": prompt},
          {"role": "user", "content": caption[:2000]},
        ],
        temperature=0.1,
        max_tokens=50,
      )

    resp = with_retry(_call, label="OpenAI classification")
    category = (resp.choices[0].message.content or "").strip().lower()
    return category if category in CONNECT3_CATEGORIES else None
  except Exception as exc:  # pragma: no cover - defensive logging
    logger.error(f"Error classifying event: {exc}")
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
    "created_at": post.get("timestamp") or datetime.now(timezone.utc).isoformat(),
  }


def embed_user(user_id: str, decay_half_life_days: float = 30.0) -> List[float]:
  """
  Compute a user embedding from interactions; falls back to preferences.
  
  Time Decay: Recent interactions are weighted more heavily using exponential decay.
  Formula: final_weight = base_weight × e^(-λ × days_old)
  Where λ = ln(2) / half_life_days (so weight halves every half_life_days)
  
  Args:
      user_id: The user's ID
      decay_half_life_days: Number of days for weight to decay by 50% (default: 30)
  """
  import math
  
  # Calculate decay constant (λ) from half-life
  decay_lambda = math.log(2) / decay_half_life_days
  now = datetime.now(timezone.utc)
  
  interactions_resp = (
    supabase.table("interactions")
    .select("event_id, interaction_type, created_at")  # Added created_at for time decay
    .eq("user_id", user_id)
    .execute()
  )
  ensure_ok(interactions_resp, action="select interactions")
  interactions = interactions_resp.data or []
  if interactions:
    base_weights = {"like": 1.0, "click": 0.5, "dislike": -0.5}
    event_ids = [i["event_id"] for i in interactions if i.get("event_id")]
    if event_ids:
      embeddings_resp = (
        supabase.table("event_embeddings")
        .select("event_id, embedding")
        .in_("event_id", event_ids)
        .execute()
      )
      ensure_ok(embeddings_resp, action="select event_embeddings")
      embs = embeddings_resp.data or []
      emb_map = {
        e["event_id"]: _parse_embedding(e.get("embedding"))
        for e in embs
        if e.get("event_id")
      }

      vec = [0.0] * EMBEDDING_DIM
      total = 0.0
      for i in interactions:
        emb_vec = emb_map.get(i.get("event_id"))
        if not emb_vec or len(emb_vec) != EMBEDDING_DIM:
          continue
        
        # Calculate time decay multiplier
        created_at_str = i.get("created_at")
        time_decay = 1.0  # Default: no decay if no timestamp
        if created_at_str:
          try:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            days_old = (now - created_at).total_seconds() / 86400  # Convert to days
            time_decay = math.exp(-decay_lambda * days_old)
          except Exception:
            pass  # Keep default decay of 1.0
        
        # Apply both base weight and time decay
        base_weight = base_weights.get(i.get("interaction_type"), 0.0)
        final_weight = base_weight * time_decay
        
        for idx, val in enumerate(emb_vec):
          vec[idx] += val * final_weight
        total += abs(final_weight)
      return [v / total for v in vec] if total else vec

  # Cold start: preferences text
  prefs_resp = supabase.table("user_preferences").select("*").eq("user_id", user_id).limit(1).execute()
  ensure_ok(prefs_resp, action="select user_preferences")
  prefs = prefs_resp.data[0] if prefs_resp.data else None
  if prefs:
    pref_mapping = {
      "tech_innovation": "technology, AI, machine learning, coding",
      "career_networking": "career development, networking, industry connections",
      "academic_workshops": "academic workshops, revision sessions, study groups",
      "social_cultural": "social events, parties, cultural activities",
      "entrepreneurship": "startups, entrepreneurship, business",
      "sports_fitness": "sports, fitness, physical activities",
      "arts_music": "arts, music, creative performances, exhibitions",
      "volunteering_community": "volunteering, community service, charity events",
      "food_dining": "food, dining, cooking, culinary experiences",
      "travel_adventure": "travel, adventure, outdoor activities, exploration",
      "health_wellness": "health, wellness, mental health, self-care",
      "environment_sustainability": "environment, sustainability, green initiatives, climate",
      "gaming_esports": "gaming, esports, video games, tournaments",
    }
    interests: List[str] = []
    for key, description in pref_mapping.items():
      score = prefs.get(key)
      if isinstance(score, (int, float)) and score > 0.6:
        interests.append(description)
    if interests:
      pref_text = f"University student interested in: {', '.join(interests)}"
    else:
      pref_text = "University student interested in general university events"
  else:
    pref_text = "University student interested in general university events"
  return generate_embedding(pref_text)
