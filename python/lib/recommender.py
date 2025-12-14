"""
Two-Tower Recommendation Engine for Connect3

This implements the full recommendation pipeline:
1. Load event embeddings
2. Compute user embedding
3. Retrieve top-N candidates via vector similarity
4. Apply business rules (recency, diversity, etc.)
5. Return final recommendations
"""
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field

from .supabase_client import supabase
from .embeddings import embedding_service, CONNECT3_CATEGORIES
from .vector_index import VectorIndex, get_event_index, SearchResult
from .config import RECOMMENDATION_CONFIG


@dataclass
class RecommendedEvent:
    event_id: str
    title: str
    caption: str
    timestamp: str
    permalink: str
    media_url: str
    category: Optional[str]
    similarity_score: float
    recency_score: float
    final_score: float
    reason: str = ""  # Why this event is recommended


@dataclass
class RecommendationConfig:
    top_k: int = 10  # Number of final recommendations
    candidate_multiplier: int = 3  # Retrieve top_k * this for re-ranking
    recency_weight: float = 0.3  # Weight for recency (0-1)
    similarity_weight: float = 0.7  # Weight for similarity (0-1)
    diversity_penalty: float = 0.1  # Penalty for same-category events
    max_days_old: int = 60  # Filter out events older than this


DEFAULT_CONFIG = RecommendationConfig()


class TwoTowerRecommender:
    """Two-tower recommendation engine using embeddings"""
    
    def __init__(self, config: Optional[RecommendationConfig] = None):
        self.event_index = get_event_index()
        self.config = config or DEFAULT_CONFIG
    
    def load_event_index(self) -> None:
        """Load event embeddings into the vector index"""
        # Fetch all event embeddings from database
        result = supabase.table("event_embeddings").select("event_id, embedding, category, created_at").execute()
        event_embeddings = result.data or []
        
        if not event_embeddings:
            print("No event embeddings found in database")
            return
        
        # Load into vector index
        self.event_index.clear()
        
        for event in event_embeddings:
            embedding = (
                json.loads(event["embedding"])
                if isinstance(event["embedding"], str)
                else event["embedding"]
            )
            
            self.event_index.add(event["event_id"], embedding, {
                "category": event.get("category"),
                "created_at": event.get("created_at")
            })
        
        print(f"Loaded {len(event_embeddings)} events into vector index")
    
    def get_recommendations(self, user_id: str) -> List[RecommendedEvent]:
        """Get recommendations for a user"""
        # Step 1: Get user embedding
        user_embedding = embedding_service.embed_user(user_id)
        
        # Step 2: Get user's past interactions to exclude
        result = supabase.table("feedback_logs").select("event_id").eq("user_id", user_id).execute()
        past_interactions = result.data or []
        exclude_ids = set(i["event_id"] for i in past_interactions)
        
        # Step 3: Retrieve candidates via vector search
        num_candidates = self.config.top_k * self.config.candidate_multiplier
        candidates = self.event_index.search(
            user_embedding.embedding,
            num_candidates,
            exclude_ids
        )
        
        if not candidates:
            return []
        
        # Step 4: Fetch full event data for candidates
        candidate_ids = [c.id for c in candidates]
        result = supabase.table("events").select("*").in_("id", candidate_ids).execute()
        events = result.data or []
        
        if not events:
            return []
        
        # Step 5: Apply business rules and re-rank
        ranked_events = self._apply_business_rules(candidates, events)
        
        # Step 6: Add recommendation reasons
        return [
            RecommendedEvent(
                event_id=e["event_id"],
                title=e["title"],
                caption=e["caption"],
                timestamp=e["timestamp"],
                permalink=e["permalink"],
                media_url=e["media_url"],
                category=e["category"],
                similarity_score=e["similarity_score"],
                recency_score=e["recency_score"],
                final_score=e["final_score"],
                reason=self._generate_recommendation_reason(e)
            )
            for e in ranked_events[:self.config.top_k]
        ]
    
    def _apply_business_rules(
        self,
        candidates: List[SearchResult],
        events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply business rules for re-ranking"""
        now = datetime.now()
        scored_events = []
        
        # Create lookup map for events
        event_map = {e["id"]: e for e in events}
        
        # Track category counts for diversity
        category_counts: Dict[str, int] = {}
        
        for candidate in candidates:
            event = event_map.get(candidate.id)
            if not event:
                continue
            
            # Calculate recency score (newer = higher)
            event_date_str = event.get("timestamp") or event.get("event_date")
            if event_date_str:
                try:
                    event_date = datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
                    days_old = abs((event_date - now).days)
                except:
                    days_old = 0
            else:
                days_old = 0
            
            # Filter out old events
            if days_old > self.config.max_days_old:
                continue
            
            # Recency score: 1 for today, decreasing with age
            recency_score = max(0, 1 - (days_old / self.config.max_days_old))
            
            # Diversity penalty
            category = event.get("category") or "unknown"
            category_count = category_counts.get(category, 0)
            diversity_penalty = category_count * self.config.diversity_penalty
            category_counts[category] = category_count + 1
            
            # Final score
            final_score = (
                (candidate.score * self.config.similarity_weight) +
                (recency_score * self.config.recency_weight) -
                diversity_penalty
            )
            
            scored_events.append({
                "event_id": event["id"],
                "title": event.get("title") or self._extract_title(event.get("caption", "")),
                "caption": event.get("caption") or event.get("description", ""),
                "timestamp": event.get("timestamp") or event.get("event_date", ""),
                "permalink": event.get("permalink") or event.get("source_url", ""),
                "media_url": event.get("media_url", ""),
                "category": event.get("category"),
                "similarity_score": candidate.score,
                "recency_score": recency_score,
                "final_score": final_score
            })
        
        # Sort by final score
        scored_events.sort(key=lambda e: e["final_score"], reverse=True)
        
        return scored_events
    
    def _extract_title(self, caption: str) -> str:
        """Extract title from caption (first line or first sentence)"""
        if not caption:
            return "Event"
        
        # Get first line
        first_line = caption.split("\n")[0]
        
        # Clean emojis and truncate
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "]+",
            flags=re.UNICODE
        )
        cleaned = emoji_pattern.sub("", first_line).strip()
        
        return cleaned[:100] + "..." if len(cleaned) > 100 else cleaned
    
    def _generate_recommendation_reason(self, event: Dict[str, Any]) -> str:
        """Generate human-readable recommendation reason"""
        reasons = []
        
        # High similarity
        sim_score = event.get("similarity_score", 0)
        if sim_score > 0.8:
            reasons.append("Matches your interests very well")
        elif sim_score > 0.6:
            reasons.append("Related to topics you enjoy")
        
        # Category-based reason
        category = event.get("category")
        if category:
            category_names = {
                "tech_workshop": "tech and coding workshops",
                "career_networking": "career and networking events",
                "hackathon": "hackathons and competitions",
                "social_event": "social activities",
                "academic_revision": "academic support",
                "recruitment": "club activities",
                "industry_talk": "industry insights",
                "sports_recreation": "sports and recreation",
                "entrepreneurship": "entrepreneurship",
                "community_service": "community events"
            }
            category_name = category_names.get(category, category)
            reasons.append(f"You've shown interest in {category_name}")
        
        # Recent event
        if event.get("recency_score", 0) > 0.8:
            reasons.append("Happening soon")
        
        return " • ".join(reasons) if reasons else "Recommended for you"
    
    def get_batch_recommendations(
        self, 
        user_ids: List[str]
    ) -> Dict[str, List[RecommendedEvent]]:
        """Get recommendations for all users (batch mode for email sending)"""
        results = {}
        
        for user_id in user_ids:
            try:
                recommendations = self.get_recommendations(user_id)
                results[user_id] = recommendations
            except Exception as e:
                print(f"Failed to get recommendations for user {user_id}: {e}")
                results[user_id] = []
        
        return results


# Singleton instance
recommender = TwoTowerRecommender()
