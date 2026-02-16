"""In-memory vector index backed by NumPy for Connect3.

Provides cosine-similarity search over a set of named vectors with optional
metadata.  Used as a fallback when pgvector is not available.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Set

import numpy as np

from .logger import get_logger

logger = get_logger(__name__)


class VectorIndex:
    """Mutable in-memory vector store with cosine-similarity search."""

    def __init__(self, dimension: int) -> None:
        self._dimension = dimension
        self._ids: List[str] = []
        self._vectors: List[np.ndarray] = []
        self._metadata: List[Dict[str, Any]] = []
        self._id_to_pos: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add(
        self,
        item_id: str,
        vector: Sequence[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add or update a vector.  If *item_id* already exists it is replaced."""
        vec = np.asarray(vector, dtype=np.float64)
        if vec.shape != (self._dimension,):
            raise ValueError(
                f"Expected dimension {self._dimension}, got {vec.shape}"
            )

        if item_id in self._id_to_pos:
            pos = self._id_to_pos[item_id]
            self._vectors[pos] = vec
            self._metadata[pos] = metadata or {}
        else:
            pos = len(self._ids)
            self._ids.append(item_id)
            self._vectors.append(vec)
            self._metadata.append(metadata or {})
            self._id_to_pos[item_id] = pos

    def remove(self, item_id: str) -> None:
        """Remove a vector by id (no-op if absent)."""
        if item_id not in self._id_to_pos:
            return
        pos = self._id_to_pos.pop(item_id)
        # Swap-remove for O(1) deletion
        last = len(self._ids) - 1
        if pos != last:
            self._ids[pos] = self._ids[last]
            self._vectors[pos] = self._vectors[last]
            self._metadata[pos] = self._metadata[last]
            self._id_to_pos[self._ids[pos]] = pos
        self._ids.pop()
        self._vectors.pop()
        self._metadata.pop()

    def clear(self) -> None:
        """Remove all vectors."""
        self._ids.clear()
        self._vectors.clear()
        self._metadata.clear()
        self._id_to_pos.clear()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def size(self) -> int:
        return len(self._ids)

    def search(
        self,
        query: Sequence[float],
        *,
        top_k: int = 10,
        exclude_ids: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Return up to *top_k* most similar items (cosine similarity)."""
        if not self._ids:
            return []

        q = np.asarray(query, dtype=np.float64)
        q_norm = np.linalg.norm(q)
        if q_norm == 0 or not np.isfinite(q_norm):
            return []

        q_unit = q / q_norm
        exclude = exclude_ids or set()

        scored: List[tuple[float, int]] = []
        for idx, vec in enumerate(self._vectors):
            if self._ids[idx] in exclude:
                continue
            v_norm = np.linalg.norm(vec)
            if v_norm == 0 or not np.isfinite(v_norm):
                continue
            sim = float(np.dot(q_unit, vec / v_norm))
            if not np.isfinite(sim):
                continue
            scored.append((sim, idx))

        scored.sort(key=lambda t: t[0], reverse=True)

        results: List[Dict[str, Any]] = []
        for sim, idx in scored[:top_k]:
            results.append(
                {
                    "id": self._ids[idx],
                    "score": sim,
                    "metadata": dict(self._metadata[idx]),
                }
            )
        return results

    def search_with_filter(
        self,
        query: Sequence[float],
        *,
        top_k: int = 10,
        predicate: Optional[Any] = None,
        exclude_ids: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Like :meth:`search`, but also applies a *predicate* on metadata."""
        if not self._ids:
            return []

        q = np.asarray(query, dtype=np.float64)
        q_norm = np.linalg.norm(q)
        if q_norm == 0 or not np.isfinite(q_norm):
            return []

        q_unit = q / q_norm
        exclude = exclude_ids or set()

        scored: List[tuple[float, int]] = []
        for idx, vec in enumerate(self._vectors):
            if self._ids[idx] in exclude:
                continue
            if predicate and not predicate(self._metadata[idx]):
                continue
            v_norm = np.linalg.norm(vec)
            if v_norm == 0 or not np.isfinite(v_norm):
                continue
            sim = float(np.dot(q_unit, vec / v_norm))
            if not np.isfinite(sim):
                continue
            scored.append((sim, idx))

        scored.sort(key=lambda t: t[0], reverse=True)

        results: List[Dict[str, Any]] = []
        for sim, idx in scored[:top_k]:
            results.append(
                {
                    "id": self._ids[idx],
                    "score": sim,
                    "metadata": dict(self._metadata[idx]),
                }
            )
        return results

    # ------------------------------------------------------------------
    # Batch helpers
    # ------------------------------------------------------------------

    def add_batch(
        self,
        entries: Sequence[Dict[str, Any]],
    ) -> None:
        """Add multiple vectors at once.

        Each entry should have ``id``, ``vector``, and optionally ``metadata``.
        """
        for entry in entries:
            self.add(
                entry["id"],
                entry["vector"],
                entry.get("metadata"),
            )
