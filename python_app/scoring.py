"""
Event scoring (Python port of src/lib/scoring.ts).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from .supabase_client import supabase

CLUSTER_MATCH_WEIGHT = 50
MAX_URGENCY_SCORE = 30


def _parse_date(value: str) -> datetime:
  try:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
  except Exception:
    return datetime.now(timezone.utc)


def _cluster_match(event: Dict[str, Any], prefs: Dict[str, Any]) -> float:
  category = event.get("category")
  if not category:
    return 0.5
  val = prefs.get(category)
  return float(val) if isinstance(val, (int, float)) else 0.5


def _urgency_score(event: Dict[str, Any]) -> float:
  event_date = _parse_date(event.get("event_date") or event.get("timestamp") or "")
  now = datetime.now(timezone.utc)
  days_until = (event_date - now).days
  return max(0, MAX_URGENCY_SCORE - days_until)


def rank_events_for_user(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
  user_resp = supabase.table("users").select("*").eq("id", user_id).limit(1).execute()
  if not user_resp.data:
    return []
  prefs_resp = supabase.table("user_preferences").select("*").eq("user_id", user_id).limit(1).execute()
  if not prefs_resp.data:
    return []
  prefs = prefs_resp.data[0]

  events_resp = supabase.table("events").select("*").gte("event_date", datetime.now(timezone.utc).isoformat()).order("event_date", desc=False).limit(100).execute()
  events = events_resp.data or []

  ranked = []
  for evt in events:
    cluster_match = _cluster_match(evt, prefs)
    urgency = _urgency_score(evt)
    score = cluster_match * CLUSTER_MATCH_WEIGHT + urgency
    ranked.append({**evt, "score": score, "cluster_match": cluster_match, "urgency_score": urgency})

  ranked.sort(key=lambda e: e["score"], reverse=True)
  return ranked[:limit]
