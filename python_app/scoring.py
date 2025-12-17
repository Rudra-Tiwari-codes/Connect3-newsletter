"""Event scoring and ranking for Connect3 (Python-first implementation)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .supabase_client import ensure_ok, supabase

CLUSTER_MATCH_WEIGHT = 50
MAX_URGENCY_SCORE = 30
DEFAULT_CATEGORY_SCORE = 0.5


def _parse_date(value: str) -> Optional[datetime]:
  try:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
  except Exception:
    return None


def _cluster_match(event: Dict[str, Any], prefs: Dict[str, Any]) -> float:
  category = event.get("category")
  if not category:
    return DEFAULT_CATEGORY_SCORE
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
  user_resp = supabase.table("users").select("*").eq("id", user_id).limit(1).execute()
  ensure_ok(user_resp, action="select users")
  if not user_resp.data:
    raise RuntimeError(f"User not found: {user_id}")

  prefs_resp = supabase.table("user_preferences").select("*").eq("user_id", user_id).limit(1).execute()
  ensure_ok(prefs_resp, action="select user_preferences")
  if not prefs_resp.data:
    raise RuntimeError(f"User preferences not found: {user_id}")
  prefs = prefs_resp.data[0]

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
    cluster_match = _cluster_match(evt, prefs)
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
