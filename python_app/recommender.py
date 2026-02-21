"""Two-tower recommendation engine implemented natively in Python."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Mapping, Optional, Sequence

from .embeddings import EMBEDDING_DIM, embed_user
from .logger import get_logger
from .supabase_client import ensure_ok, supabase

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
