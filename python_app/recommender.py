"""Two-tower recommendation engine implemented natively in Python."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Mapping, Optional, Sequence

from .embeddings import EMBEDDING_DIM, embed_user
from .logger import get_logger
from .pgvector_search import is_pgvector_available, search_similar_events
from .supabase_client import ensure_ok, supabase
from .vector_index import VectorIndex

logger = get_logger(__name__)


@dataclass
class RecommendationConfig:
  top_k: int = 10
  candidate_multiplier: int = 3
  recency_weight: float = 0.3
  similarity_weight: float = 0.7
  diversity_penalty: float = 0.1
  max_days_old: int = 365  # Increased to accommodate test data with varied timestamps

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
  except Exception as e:
    logger.warning(f"Failed to parse date value '{value}': {e}")
    return None


class TwoTowerRecommender:
  """Retrieve personalized event recommendations using vector similarity plus business rules."""

  def __init__(self, config: Optional[Mapping[str, object]] = None, index: Optional[VectorIndex] = None) -> None:
    self.config = RecommendationConfig.from_overrides(config)
    self.index = index or VectorIndex(EMBEDDING_DIM)
    self._events_cache: Dict[str, Dict[str, object]] = {}
    self._use_pgvector = is_pgvector_available()
    if self._use_pgvector:
      logger.info("Using pgvector for similarity search")
    else:
      logger.info("Using in-memory NumPy for similarity search")
    # Event details are loaded lazily from Supabase when needed.

  def _load_events_from_supabase(self, event_ids: Sequence[str]) -> None:
    """Load event details from Supabase into the local cache."""
    missing_ids = [event_id for event_id in event_ids if event_id and event_id not in self._events_cache]
    if not missing_ids:
      return

    batch_size = 200
    for start in range(0, len(missing_ids), batch_size):
      batch = missing_ids[start:start + batch_size]
      resp = supabase.table("events").select("*").in_("id", batch).execute()
      ensure_ok(resp, action="select events")
      rows = resp.data or []
      for row in rows:
        row_id = row.get("id") or row.get("event_id")
        if row_id is None:
          continue
        self._events_cache[str(row_id)] = row

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
    user_vector = embed_user(user_id)
    if not user_vector:
      return []

    # Exclude events the user already interacted with
    feedback_resp = supabase.table("interactions").select("event_id").eq("subscriber_id", user_id).execute()
    ensure_ok(feedback_resp, action="select interactions")
    feedback = feedback_resp.data or []
    exclude_ids = {row["event_id"] for row in feedback if "event_id" in row}

    candidate_count = self.config.top_k * self.config.candidate_multiplier
    
    # Try pgvector first, fall back to in-memory index
    if self._use_pgvector:
      candidates = search_similar_events(
        user_vector,
        top_k=candidate_count,
        threshold=0.3,
        exclude_ids=exclude_ids
      )
    else:
      if self.index.size() == 0:
        self.load_event_index()
      candidates = self.index.search(user_vector, top_k=candidate_count, exclude_ids=exclude_ids)
    
    if not candidates:
      return []

    candidate_ids = [str(c.get("id")) for c in candidates if c.get("id")]
    candidate_meta_by_id = {
      str(c.get("id")): c.get("metadata") for c in candidates if c.get("id")
    }
    
    # Load event details from Supabase as needed.
    self._load_events_from_supabase(candidate_ids)

    event_map: Dict[str, Dict[str, object]] = {}
    for cid in candidate_ids:
      if cid in self._events_cache:
        event = dict(self._events_cache[cid])
        # Add category from candidate metadata
        candidate_meta = candidate_meta_by_id.get(cid, {})
        if candidate_meta and candidate_meta.get("category"):
          event["category"] = candidate_meta["category"]
        event_map[cid] = event

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
        logger.error(f"Failed to get recommendations for user {uid}: {exc}")
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
      event_id = str(candidate["id"])
      event = events.get(event_id)
      if not event:
        continue

      event_date = _parse_date(
        event.get("event_date")
        or event.get("timestamp")
        or event.get("date")
        or event.get("created_at")
      )
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
        "timestamp": event.get("timestamp") or event.get("event_date") or event.get("date"),
        "permalink": event.get("permalink") or event.get("source_url") or event.get("url"),
        "media_url": event.get("media_url") or event.get("image_url") or event.get("image") or "",
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
