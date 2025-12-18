"""Two-tower recommendation engine implemented natively in Python."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Mapping, Optional, Sequence

from .embeddings import EMBEDDING_DIM, embed_user
from .supabase_client import ensure_ok, supabase
from .vector_index import VectorIndex


@dataclass
class RecommendationConfig:
  top_k: int = 10
  candidate_multiplier: int = 3
  recency_weight: float = 0.3
  similarity_weight: float = 0.7
  diversity_penalty: float = 0.1
  max_days_old: int = 60

  @classmethod
  def from_overrides(cls, overrides: Optional[Mapping[str, object]] = None) -> "RecommendationConfig":
    base = cls()
    if not overrides:
      return base
    for key, value in overrides.items():
      if hasattr(base, key):
        setattr(base, key, value)  # type: ignore[arg-type]
    return base


def _parse_date(value: Optional[str]) -> Optional[datetime]:
  if not value:
    return None
  try:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
  except Exception:
    return None


class TwoTowerRecommender:
  """Retrieve personalized event recommendations using vector similarity plus business rules."""

  def __init__(self, config: Optional[Mapping[str, object]] = None, index: Optional[VectorIndex] = None) -> None:
    self.config = RecommendationConfig.from_overrides(config)
    self.index = index or VectorIndex(EMBEDDING_DIM)

  def load_event_index(self) -> int:
    """Load all event embeddings from Supabase into the in-memory index."""
    resp = supabase.table("event_embeddings").select("event_id, embedding, category, created_at").execute()
    ensure_ok(resp, action="select event_embeddings")
    rows = resp.data or []
    self.index.clear()

    for row in rows:
      emb = row.get("embedding")
      if isinstance(emb, str):
        try:
          emb = json.loads(emb)
        except Exception:
          continue
      if not isinstance(emb, list):
        continue
      if len(emb) != EMBEDDING_DIM:
        continue
      self.index.add(
        row["event_id"],
        emb,
        {
          "category": row.get("category"),
          "created_at": row.get("created_at"),
        },
      )

    return len(rows)

  def get_recommendations(self, user_id: str) -> List[Dict[str, object]]:
    if self.index.size() == 0:
      self.load_event_index()

    user_vector = embed_user(user_id)
    if not user_vector:
      return []

    # Exclude events the user already interacted with
    feedback_resp = supabase.table("feedback_logs").select("event_id").eq("user_id", user_id).execute()
    ensure_ok(feedback_resp, action="select feedback_logs")
    feedback = feedback_resp.data or []
    exclude_ids = {row["event_id"] for row in feedback if "event_id" in row}

    candidate_count = self.config.top_k * self.config.candidate_multiplier
    candidates = self.index.search(user_vector, top_k=candidate_count, exclude_ids=exclude_ids)
    if not candidates:
      return []

    candidate_ids = [c.get("id") for c in candidates if c.get("id")]
    events_resp = supabase.table("events").select("*").in_("id", candidate_ids).execute()
    ensure_ok(events_resp, action="select events")
    events = events_resp.data or []
    event_map = {evt["id"]: evt for evt in events if "id" in evt}

    ranked = self._apply_business_rules(candidates, event_map)
    return ranked[: self.config.top_k]

  def get_batch_recommendations(self, user_ids: Sequence[str]) -> Dict[str, List[Dict[str, object]]]:
    if self.index.size() == 0:
      self.load_event_index()

    results: Dict[str, List[Dict[str, object]]] = {}
    for uid in user_ids:
      try:
        results[uid] = self.get_recommendations(uid)
      except Exception as exc:
        print(f"Failed to get recommendations for user {uid}: {exc}")
        results[uid] = []
    return results

  def _apply_business_rules(
    self,
    candidates: Sequence[Dict[str, object]],
    events: Mapping[str, Mapping[str, object]],
  ) -> List[Dict[str, object]]:
    now = datetime.now(timezone.utc)
    results: List[Dict[str, object]] = []
    category_counts: Dict[str, int] = {}

    for candidate in candidates:
      event_id = candidate["id"]
      event = events.get(event_id)
      if not event:
        continue

      event_date = _parse_date(event.get("event_date") or event.get("timestamp") or event.get("created_at"))
      if not event_date:
        continue
      days_old = abs((event_date - now).days)
      if days_old > self.config.max_days_old:
        continue

      recency_score = max(0.0, 1.0 - (days_old / self.config.max_days_old))
      category = event.get("category") or "unknown"
      diversity_penalty = category_counts.get(category, 0) * self.config.diversity_penalty
      category_counts[category] = category_counts.get(category, 0) + 1

      final_score = (
        float(candidate["score"]) * self.config.similarity_weight
        + recency_score * self.config.recency_weight
        - diversity_penalty
      )

      recommendation = {
        "event_id": event_id,
        "title": event.get("title") or self._extract_title(event.get("caption") or event.get("description") or ""),
        "caption": event.get("caption") or event.get("description") or "",
        "timestamp": event.get("timestamp") or event.get("event_date"),
        "permalink": event.get("permalink") or event.get("source_url"),
        "media_url": event.get("media_url") or "",
        "category": event.get("category"),
        "similarity_score": candidate["score"],
        "recency_score": recency_score,
        "final_score": final_score,
      }
      recommendation["reason"] = self._generate_reason(recommendation)
      results.append(recommendation)

    results.sort(key=lambda r: r["final_score"], reverse=True)
    return results

  def _extract_title(self, caption: str) -> str:
    if not caption:
      return "Event"
    first_line = caption.split("\n", 1)[0]
    cleaned = first_line.encode("ascii", errors="ignore").decode("ascii").strip()
    return cleaned[:100] + ("..." if len(cleaned) > 100 else "")

  def _generate_reason(self, event: Mapping[str, object]) -> str:
    reasons: List[str] = []

    sim = float(event.get("similarity_score") or 0)
    recency = float(event.get("recency_score") or 0)
    category = event.get("category")

    if sim > 0.8:
      reasons.append("Matches your interests closely")
    elif sim > 0.6:
      reasons.append("Related to topics you enjoy")

    if category:
      reasons.append(f"Includes {category.replace('_', ' ')} content")

    if recency > 0.8:
      reasons.append("Happening soon")

    return " • ".join(reasons) if reasons else "Recommended for you"


recommender = TwoTowerRecommender()
