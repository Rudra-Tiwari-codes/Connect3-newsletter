"""
FAISS-like Vector Index for Event Embeddings

Since FAISS requires native bindings, we implement a simple but efficient
in-memory vector index using brute-force search with optimizations.

For production at scale, consider:
- Pinecone (managed vector DB)
- Weaviate
- Milvus
- pgvector (PostgreSQL extension)

For Connect3's scale (~1000 events, ~10000 users), this in-memory
approach is perfectly fine and fast.
"""
import json
import math
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field

from .config import EMBEDDING_CONFIG


@dataclass
class VectorEntry:
    id: str
    vector: List[float]
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SearchResult:
    id: str
    score: float
    metadata: Optional[Dict[str, Any]] = None


class VectorIndex:
    """In-memory vector index with cosine similarity search"""
    
    def __init__(self, dimension: int = EMBEDDING_CONFIG.EMBEDDING_DIM):
        self.dimension = dimension
        self._vectors: Dict[str, VectorEntry] = {}
    
    def add(self, id: str, vector: List[float], metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a vector to the index"""
        if len(vector) != self.dimension:
            raise ValueError(f"Vector dimension mismatch: expected {self.dimension}, got {len(vector)}")
        self._vectors[id] = VectorEntry(id=id, vector=vector, metadata=metadata)
    
    def add_batch(self, entries: List[VectorEntry]) -> None:
        """Add multiple vectors at once"""
        for entry in entries:
            self.add(entry.id, entry.vector, entry.metadata)
    
    def remove(self, id: str) -> bool:
        """Remove a vector from the index"""
        if id in self._vectors:
            del self._vectors[id]
            return True
        return False
    
    def get(self, id: str) -> Optional[VectorEntry]:
        """Get a vector by ID"""
        return self._vectors.get(id)
    
    def has(self, id: str) -> bool:
        """Check if vector exists"""
        return id in self._vectors
    
    def size(self) -> int:
        """Get total number of vectors"""
        return len(self._vectors)
    
    def search(
        self, 
        query_vector: List[float], 
        top_k: int = 10, 
        exclude_ids: Optional[Set[str]] = None
    ) -> List[SearchResult]:
        """Search for top-K most similar vectors using cosine similarity"""
        if len(query_vector) != self.dimension:
            raise ValueError(f"Query vector dimension mismatch: expected {self.dimension}, got {len(query_vector)}")
        
        exclude_ids = exclude_ids or set()
        
        # Pre-compute query norm for efficiency
        query_norm = math.sqrt(sum(x * x for x in query_vector))
        
        results: List[SearchResult] = []
        
        for id, entry in self._vectors.items():
            if id in exclude_ids:
                continue
            
            # Cosine similarity
            dot_product = sum(q * v for q, v in zip(query_vector, entry.vector))
            vector_norm = math.sqrt(sum(v * v for v in entry.vector))
            
            if query_norm * vector_norm == 0:
                similarity = 0.0
            else:
                similarity = dot_product / (query_norm * vector_norm)
            
            results.append(SearchResult(
                id=id,
                score=similarity,
                metadata=entry.metadata
            ))
        
        # Sort by score descending and take top K
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def search_with_filter(
        self,
        query_vector: List[float],
        top_k: int,
        filter_fn: Callable[[Optional[Dict[str, Any]]], bool]
    ) -> List[SearchResult]:
        """Search with filtering by metadata"""
        if len(query_vector) != self.dimension:
            raise ValueError("Query vector dimension mismatch")
        
        query_norm = math.sqrt(sum(x * x for x in query_vector))
        results: List[SearchResult] = []
        
        for id, entry in self._vectors.items():
            # Apply filter
            if not filter_fn(entry.metadata):
                continue
            
            dot_product = sum(q * v for q, v in zip(query_vector, entry.vector))
            vector_norm = math.sqrt(sum(v * v for v in entry.vector))
            
            if query_norm * vector_norm == 0:
                similarity = 0.0
            else:
                similarity = dot_product / (query_norm * vector_norm)
            
            results.append(SearchResult(
                id=id,
                score=similarity,
                metadata=entry.metadata
            ))
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    def to_json(self) -> str:
        """Serialize index to JSON for storage"""
        entries = [
            {"id": e.id, "vector": e.vector, "metadata": e.metadata}
            for e in self._vectors.values()
        ]
        return json.dumps({
            "dimension": self.dimension,
            "entries": entries
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> "VectorIndex":
        """Load index from JSON"""
        data = json.loads(json_str)
        index = cls(data["dimension"])
        for entry in data["entries"]:
            index.add(entry["id"], entry["vector"], entry.get("metadata"))
        return index
    
    def clear(self) -> None:
        """Clear all vectors"""
        self._vectors.clear()
    
    def get_all_ids(self) -> List[str]:
        """Get all IDs in the index"""
        return list(self._vectors.keys())


# Global singleton index for events
_event_index: Optional[VectorIndex] = None


def get_event_index() -> VectorIndex:
    """Get the global event index singleton"""
    global _event_index
    if _event_index is None:
        _event_index = VectorIndex(EMBEDDING_CONFIG.EMBEDDING_DIM)
    return _event_index


def reset_event_index() -> None:
    """Reset the global event index"""
    global _event_index
    _event_index = None
