"""Pgvector-backed similarity search for Connect3.

Wraps the Supabase ``match_events`` RPC function that performs cosine
similarity search using the pgvector extension.  Falls back gracefully
when pgvector is not available.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from .config import get_env
from .logger import get_logger
from .supabase_client import supabase

logger = get_logger(__name__)

# Feature flag – can be disabled via env var
USE_PGVECTOR: bool = (get_env("USE_PGVECTOR", "false") or "false").lower() in (
    "1",
    "true",
    "yes",
)


def is_pgvector_available() -> bool:
    """Return ``True`` if the pgvector RPC is reachable."""
    if not USE_PGVECTOR:
        return False
    try:
        supabase.rpc("match_events", {
            "query_embedding": [0.0] * 3,
            "match_count": 1,
            "match_threshold": 0.0,
        }).execute()
        return True
    except Exception:
        logger.debug("pgvector RPC not available – falling back to in-memory index")
        return False


def search_similar_events(
    query_embedding: List[float],
    *,
    top_k: int = 10,
    threshold: float = 0.5,
    exclude_ids: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """Search for similar events using the pgvector ``match_events`` RPC.

    Returns a list of dicts with keys ``id``, ``score``, ``category``, and
    ``metadata``.  Returns an empty list when pgvector is disabled or on
    error.
    """
    if not USE_PGVECTOR:
        return []

    try:
        resp = supabase.rpc(
            "match_events",
            {
                "query_embedding": query_embedding,
                "match_count": top_k,
                "match_threshold": threshold,
            },
        ).execute()

        rows = resp.data or []
        exclude = exclude_ids or set()

        results: List[Dict[str, Any]] = []
        for row in rows:
            event_id = row.get("event_id")
            if event_id in exclude:
                continue
            results.append(
                {
                    "id": event_id,
                    "score": row.get("similarity", 0.0),
                    "category": row.get("category"),
                    "metadata": {
                        "category": row.get("category"),
                        "created_at": row.get("created_at"),
                    },
                }
            )
        return results[:top_k]
    except Exception as exc:
        logger.error("pgvector search failed: %s", exc)
        return []


def upsert_embedding_pgvector(
    event_id: str, embedding: List[float], category: Optional[str] = None
) -> bool:
    """Upsert an event embedding into the pgvector table.

    Returns ``True`` on success, ``False`` when pgvector is disabled or on
    error.
    """
    if not USE_PGVECTOR:
        return False

    try:
        supabase.table("event_embeddings").upsert(
            {
                "event_id": event_id,
                "embedding": embedding,
                "category": category,
            }
        ).execute()
        return True
    except Exception as exc:
        logger.error("pgvector upsert failed for %s: %s", event_id, exc)
        return False
