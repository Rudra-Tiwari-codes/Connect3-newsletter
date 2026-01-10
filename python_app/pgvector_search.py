"""
pgvector-based similarity search for Connect3.

Provides database-native vector similarity search using Supabase's pgvector extension.
Falls back to in-memory NumPy search if pgvector is not available.
"""

from typing import Any, Dict, List, Optional, Set

from .logger import get_logger
from .supabase_client import supabase

logger = get_logger(__name__)

# Configuration
USE_PGVECTOR = True
PGVECTOR_TABLE = "event_embeddings_v2"


def search_similar_events(
    query_embedding: List[float],
    top_k: int = 10,
    threshold: float = 0.5,
    category_filter: Optional[str] = None,
    exclude_ids: Optional[Set[str]] = None
) -> List[Dict[str, Any]]:
    """
    Search for similar events using pgvector's native similarity search.
    
    This uses the match_events database function created in the migration,
    which performs cosine similarity search using IVFFlat indexing.
    
    Args:
        query_embedding: 1536-dimensional query vector
        top_k: Number of results to return
        threshold: Minimum similarity score (0-1)
        category_filter: Optional category to filter by
        exclude_ids: Event IDs to exclude from results
        
    Returns:
        List of matching events with similarity scores
    """
    exclude_ids = exclude_ids or set()
    
    if not USE_PGVECTOR:
        logger.debug("pgvector disabled, falling back to in-memory search")
        return []
    
    try:
        # Call the match_events database function
        # The function expects: query_embedding, match_threshold, match_count, category_filter
        response = supabase.rpc(
            'match_events',
            {
                'query_embedding': query_embedding,
                'match_threshold': threshold,
                'match_count': top_k + len(exclude_ids),  # Fetch extra to account for exclusions
                'category_filter': category_filter
            }
        ).execute()
        
        if not response.data:
            return []
        
        # Filter excluded IDs and format results
        results = []
        for row in response.data:
            event_id = row.get('event_id')
            if event_id and event_id not in exclude_ids:
                results.append({
                    'id': event_id,
                    'event_id': event_id,
                    'category': row.get('category'),
                    'score': float(row.get('similarity', 0)),
                    'metadata': {'category': row.get('category')}
                })
                if len(results) >= top_k:
                    break
        
        logger.debug(f"pgvector search returned {len(results)} results")
        return results
        
    except Exception as e:
        logger.warning(f"pgvector search failed, may need migration: {e}")
        return []


def upsert_embedding_pgvector(
    event_id: str,
    embedding: List[float],
    category: Optional[str] = None
) -> bool:
    """
    Upsert an event embedding using pgvector format.
    
    Args:
        event_id: Unique event identifier
        embedding: 1536-dimensional embedding vector
        category: Event category
        
    Returns:
        True if successful, False otherwise
    """
    if not USE_PGVECTOR:
        return False
    
    try:
        # Format embedding as PostgreSQL vector literal
        embedding_str = f"[{','.join(str(x) for x in embedding)}]"
        
        response = supabase.table(PGVECTOR_TABLE).upsert(
            {
                'event_id': event_id,
                'embedding': embedding_str,
                'category': category
            },
            on_conflict='event_id'
        ).execute()
        
        logger.debug(f"Upserted embedding for event {event_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to upsert pgvector embedding: {e}")
        return False


def is_pgvector_available() -> bool:
    """Check if pgvector is properly configured and accessible."""
    if not USE_PGVECTOR:
        return False
    
    try:
        # Try to call the match_events function with a dummy query
        # This will fail if pgvector isn't set up
        response = supabase.rpc(
            'match_events',
            {
                'query_embedding': [0.0] * 1536,
                'match_threshold': 0.99,
                'match_count': 1
            }
        ).execute()
        return True
    except Exception as e:
        logger.info(f"pgvector not available: {e}")
        return False
