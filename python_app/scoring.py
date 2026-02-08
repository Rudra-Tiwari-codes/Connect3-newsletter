"""Event scoring and ranking for Connect3 (Python-first implementation).

Includes time decay for user preferences: recent interactions are weighted
more heavily than older ones using exponential decay.
"""

import math
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from .supabase_client import ensure_ok, supabase
from .logger import get_logger
from .categories import CONNECT3_CATEGORIES

logger = get_logger(__name__)

# 13 categories total - uniform distribution baseline
NUM_CATEGORIES = 13
DEFAULT_CATEGORY_SCORE = 1.0 / NUM_CATEGORIES  # ~0.077 (uniform probability)

CLUSTER_MATCH_WEIGHT = 50
MAX_URGENCY_SCORE = 30
DECAY_HALF_LIFE_DAYS = 30.0  # Interaction weight halves every 30 days


def _parse_date(value: str) -> Optional[datetime]:
  try:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
  except Exception:
    return None


def _compute_time_decayed_preferences(
    user_id: str,
    half_life_days: float = DECAY_HALF_LIFE_DAYS
) -> Dict[str, float]:
  """
  Compute category preferences with time decay from interaction history.
  
  Recent interactions contribute more to category scores than older ones.
  Uses exponential decay: weight = e^(-λ × days_old)
  
  Returns:
      Dict mapping category names to scores (0.0 to 1.0), normalized to sum to 1.
  """
  decay_lambda = math.log(2) / half_life_days
  now = datetime.now(timezone.utc)
  
  # Fetch interactions with timestamps and event categories
  interactions_resp = (
    supabase.table("interactions")
    .select("event_id, interaction_type, created_at")
    .eq("user_id", user_id)
    .execute()
  )
  ensure_ok(interactions_resp, action="select interactions")
  interactions = interactions_resp.data or []
  
  if not interactions:
    return {}  # Will fall back to stored preferences
  
  # Get event categories for these interactions
  event_ids = [i["event_id"] for i in interactions if i.get("event_id")]
  if not event_ids:
    return {}
  
  events_resp = (
    supabase.table("event_embeddings")
    .select("event_id, category")
    .in_("event_id", event_ids)
    .execute()
  )
  ensure_ok(events_resp, action="select event_embeddings")
  event_categories = {e["event_id"]: e.get("category") for e in (events_resp.data or [])}
  
  # Compute time-decayed scores per category
  category_scores: Dict[str, float] = {}
  category_weights: Dict[str, float] = {}
  
  base_weights = {"like": 1.0, "click": 0.5, "dislike": -0.5}
  
  for interaction in interactions:
    category = event_categories.get(interaction.get("event_id"))
    if not category:
      continue
    
    # Calculate time decay
    created_at_str = interaction.get("created_at")
    time_decay = 1.0
    if created_at_str:
      try:
        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        days_old = (now - created_at).total_seconds() / 86400
        time_decay = math.exp(-decay_lambda * days_old)
      except Exception:
        logger.warning(f"Failed to parse created_at timestamp: {created_at_str}")
    
    # Apply weight
    base_weight = base_weights.get(interaction.get("interaction_type"), 0.0)
    weighted_score = base_weight * time_decay
    
    if category not in category_scores:
      category_scores[category] = 0.0
      category_weights[category] = 0.0
    
    category_scores[category] += weighted_score
    category_weights[category] += abs(time_decay)  # Track total weight for normalization
  
  # Normalize to 0.0-1.0 range (sigmoid-like transformation)
  # Score of 0 -> 0.5, positive -> toward 1.0, negative -> toward 0.0
  result: Dict[str, float] = {}
  for cat in CONNECT3_CATEGORIES:
    if cat in category_scores:
      total_weight = category_weights.get(cat, 1.0)
      if total_weight > 0:
        normalized = category_scores[cat] / total_weight  # Range roughly -1 to 1
        # Transform to 0-1 range: (normalized + 1) / 2, clamped
        result[cat] = max(0.0, min(1.0, (normalized + 1) / 2))
      else:
        result[cat] = DEFAULT_CATEGORY_SCORE
    else:
      result[cat] = DEFAULT_CATEGORY_SCORE

  total = sum(result.values())
  if total <= 0:
    return {cat: DEFAULT_CATEGORY_SCORE for cat in CONNECT3_CATEGORIES}

  return {cat: result[cat] / total for cat in CONNECT3_CATEGORIES}


def _cluster_match(event: Dict[str, Any], prefs: Dict[str, Any], decayed_prefs: Dict[str, float]) -> float:
  """
  Get preference score for event category.
  
  Uses time-decayed preferences if available, otherwise falls back to stored preferences.
  """
  category = event.get("category")
  if not category:
    return DEFAULT_CATEGORY_SCORE
  
  # Prefer time-decayed score if available
  if category in decayed_prefs:
    return decayed_prefs[category]
  
  # Fall back to stored preferences
  val = prefs.get(category)
  return float(val) if isinstance(val, (int, float)) else DEFAULT_CATEGORY_SCORE


def _urgency_score(event: Dict[str, Any]) -> float:
  event_date = _parse_date(event.get("event_date") or event.get("timestamp") or "")
  if not event_date:
    return 0.0
  now = datetime.now(timezone.utc)
  days_until = (event_date - now).days
  return max(0, MAX_URGENCY_SCORE - days_until)


def rank_events_for_user(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
  user_resp = supabase.table("profiles").select("*").eq("id", user_id).limit(1).execute()
  ensure_ok(user_resp, action="select profiles")
  if not user_resp.data:
    raise RuntimeError(f"User not found: {user_id}")

  prefs_resp = supabase.table("user_preferences").select("*").eq("user_id", user_id).limit(1).execute()
  ensure_ok(prefs_resp, action="select user_preferences")
  if not prefs_resp.data:
    raise RuntimeError(f"User preferences not found: {user_id}")
  prefs = prefs_resp.data[0]
  
  # Compute time-decayed preferences from interaction history
  decayed_prefs = _compute_time_decayed_preferences(user_id)

  events_resp = (
    supabase.table("events")
    .select("*")
    .gte("event_date", datetime.now(timezone.utc).isoformat())
    .order("event_date", desc=False)
    .limit(100)
    .execute()
  )
  ensure_ok(events_resp, action="select events")
  events = events_resp.data or []

  ranked = []
  for evt in events:
    cluster_match = _cluster_match(evt, prefs, decayed_prefs)
    urgency = _urgency_score(evt)
    score = cluster_match * CLUSTER_MATCH_WEIGHT + urgency
    ranked.append({**evt, "score": score, "cluster_match": cluster_match, "urgency_score": urgency})

  ranked.sort(key=lambda e: e["score"], reverse=True)
  return ranked[:limit]


class EventScoringService:
  """Mirror of the TypeScript EventScoringService."""

  def rank_events_for_user(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    return rank_events_for_user(user_id, limit)

  def get_recommendations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    return self.rank_events_for_user(user_id, limit)
