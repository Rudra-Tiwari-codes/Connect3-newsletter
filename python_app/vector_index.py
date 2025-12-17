"""Lightweight in-memory vector index with cosine search."""

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple


Vector = List[float]


class VectorIndex:
  def __init__(self, dimension: int):
    self.dimension = dimension
    self.vectors: Dict[str, Tuple[Vector, Optional[Dict[str, Any]]]] = {}

  def add(self, vector_id: str, vector: Sequence[float], metadata: Optional[Dict[str, Any]] = None) -> None:
    if len(vector) != self.dimension:
      raise ValueError(f"Vector dimension mismatch: expected {self.dimension}, got {len(vector)}")
    self.vectors[vector_id] = (list(vector), metadata)

  def add_batch(self, entries: List[Dict[str, Any]]) -> None:
    for entry in entries:
      self.add(entry["id"], entry["vector"], entry.get("metadata"))

  def remove(self, vector_id: str) -> None:
    self.vectors.pop(vector_id, None)

  def clear(self) -> None:
    self.vectors.clear()

  def size(self) -> int:
    return len(self.vectors)

  def search(self, query: Sequence[float], top_k: int = 10, exclude_ids: Optional[set] = None) -> List[Dict[str, Any]]:
    exclude_ids = exclude_ids or set()
    if len(query) != self.dimension:
      raise ValueError(f"Query vector dimension mismatch: expected {self.dimension}, got {len(query)}")

    q_norm = math.sqrt(sum(x * x for x in query))
    results: List[Dict[str, Any]] = []
    for vid, (vec, metadata) in self.vectors.items():
      if vid in exclude_ids:
        continue
      dot = sum(a * b for a, b in zip(query, vec))
      v_norm = math.sqrt(sum(x * x for x in vec))
      score = dot / (q_norm * v_norm) if q_norm and v_norm else 0.0
      results.append({"id": vid, "score": score, "metadata": metadata})

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]

  def search_with_filter(self, query: Sequence[float], top_k: int, predicate) -> List[Dict[str, Any]]:
    if len(query) != self.dimension:
      raise ValueError(f"Query vector dimension mismatch: expected {self.dimension}, got {len(query)}")
    filtered = {vid: (vec, meta) for vid, (vec, meta) in self.vectors.items() if predicate(meta)}
    q_norm = math.sqrt(sum(x * x for x in query))
    results: List[Dict[str, Any]] = []
    for vid, (vec, meta) in filtered.items():
      dot = sum(a * b for a, b in zip(query, vec))
      v_norm = math.sqrt(sum(x * x for x in vec))
      score = dot / (q_norm * v_norm) if q_norm and v_norm else 0.0
      results.append({"id": vid, "score": score, "metadata": meta})
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]
