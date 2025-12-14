"""
Event Scoring Service for Connect3

Ranks events for users based on:
- Cluster match (how well event matches user preferences)
- Urgency score (days until event)
"""
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass

from .supabase_client import supabase, RankedEvent, EVENT_CATEGORIES
from .config import SCORING_CONFIG


class EventScoringService:
    """Service for scoring and ranking events for users"""
    
    async def rank_events_for_user(self, user_id: str, limit: int = 10) -> List[RankedEvent]:
        """
        Rank events for a specific user
        Score = (ClusterMatch × CLUSTER_MATCH_WEIGHT) + (MAX_URGENCY_SCORE - DaysUntilEvent)
        """
        # Fetch user data
        result = supabase.table("users").select("*").eq("id", user_id).single().execute()
        if not result.data:
            raise ValueError(f"Failed to fetch user: {user_id}")
        user = result.data
        
        # Fetch user preferences
        result = supabase.table("user_preferences").select("*").eq("user_id", user_id).single().execute()
        if not result.data:
            raise ValueError(f"Failed to fetch preferences for user: {user_id}")
        preferences = result.data
        
        # Fetch upcoming events
        now = datetime.now().isoformat()
        result = supabase.table("events").select("*").gte("event_date", now).order("event_date").limit(100).execute()
        events = result.data or []
        
        # Score each event
        ranked_events = []
        for event in events:
            cluster_match = self._calculate_cluster_match(event, preferences)
            urgency_score = self._calculate_urgency_score(event)
            score = cluster_match * SCORING_CONFIG.CLUSTER_MATCH_WEIGHT + urgency_score
            
            ranked_events.append(RankedEvent(
                id=event["id"],
                title=event["title"],
                event_date=event["event_date"],
                created_at=event.get("created_at", ""),
                updated_at=event.get("updated_at", ""),
                description=event.get("description"),
                location=event.get("location"),
                category=event.get("category"),
                tags=event.get("tags"),
                source_url=event.get("source_url"),
                score=score,
                cluster_match=cluster_match,
                urgency_score=urgency_score
            ))
        
        # Sort by score and return top N
        ranked_events.sort(key=lambda e: e.score, reverse=True)
        return ranked_events[:limit]
    
    async def rank_events_for_cluster(
        self, 
        cluster_id: int, 
        limit: int = 10
    ) -> Dict[str, List[RankedEvent]]:
        """Rank events for all users in a specific cluster"""
        # Fetch all users in the cluster
        result = supabase.table("users").select("*").eq("pca_cluster_id", cluster_id).execute()
        users = result.data or []
        
        # Rank events for each user
        results = {}
        for user in users:
            try:
                ranked_events = await self.rank_events_for_user(user["id"], limit)
                results[user["id"]] = ranked_events
            except Exception as e:
                print(f"Failed to rank events for user {user['id']}: {e}")
        
        return results
    
    def _calculate_cluster_match(self, event: Dict[str, Any], preferences: Dict[str, Any]) -> float:
        """Calculate how well an event matches user preferences (0-1 scale)"""
        category = event.get("category")
        if not category:
            return 0.5  # Default neutral match
        
        # Validate that the category exists in EVENT_CATEGORIES
        if category not in EVENT_CATEGORIES:
            return 0.5  # Default if category is not valid
        
        # Get preference value for this category
        preference_value = preferences.get(category)
        if isinstance(preference_value, (int, float)):
            return float(preference_value)
        
        return 0.5  # Default if category not found in preferences
    
    def _calculate_urgency_score(self, event: Dict[str, Any]) -> float:
        """
        Calculate urgency score based on days until event
        Returns: MAX_URGENCY_SCORE - daysUntilEvent (capped at 0 minimum)
        """
        now = datetime.now()
        event_date = datetime.fromisoformat(event["event_date"].replace("Z", "+00:00"))
        days_until = (event_date - now).days
        
        return max(0, SCORING_CONFIG.MAX_URGENCY_SCORE - days_until)
    
    async def get_recommendations(self, user_id: str, limit: int = 10) -> List[RankedEvent]:
        """Get event recommendations for a user (alias for rank_events_for_user)"""
        return await self.rank_events_for_user(user_id, limit)


# Singleton instance
event_scoring_service = EventScoringService()
