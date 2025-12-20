"""
Two-Phase Newsletter Delivery System

Phase 1: Send 9 random events for discovery (exploration)
Phase 2: Use Two-Tower recommender for semantic matching (exploitation)

The Two-Tower approach uses OpenAI embeddings to find events that are 
semantically similar to what the user liked in Phase 1, rather than 
just matching categories.

Optimized: Uses batch category fetching and NumPy vector search.
"""

import json
import random
import time
from collections import Counter
from typing import Dict, List, Any, Optional

from python_app.email_sender import send_email
from python_app.email_templates import generate_personalized_email
from python_app.supabase_client import supabase, ensure_ok
from python_app.recommender import TwoTowerRecommender


class CategoryCache:
    """
    Batch-fetches all event categories at once to avoid N+1 query problem.
    
    Instead of calling the database once per event (N calls), this fetches
    all categories in a single query and caches them for O(1) lookups.
    """
    
    def __init__(self):
        self._cache: Dict[str, str] = {}
        self._loaded = False
    
    def load_all(self, event_ids: Optional[List[str]] = None) -> None:
        """
        Load all categories from the database in a single query.
        
        Args:
            event_ids: Optional list of specific event IDs to fetch.
                       If None, fetches ALL categories.
        """
        try:
            if event_ids:
                # Fetch only specific events (still much better than N queries)
                resp = supabase.table("event_embeddings").select("event_id, category").in_("event_id", event_ids).execute()
            else:
                # Fetch all categories at once
                resp = supabase.table("event_embeddings").select("event_id, category").execute()
            
            if resp.data:
                for row in resp.data:
                    event_id = row.get("event_id")
                    category = row.get("category")
                    if event_id:
                        self._cache[event_id] = category or "general"
            
            self._loaded = True
            print(f"  CategoryCache: Loaded {len(self._cache)} categories in 1 query")
        except Exception as e:
            print(f"  Warning: Failed to batch load categories: {e}")
            self._loaded = True  # Prevent retry loops
    
    def get(self, event_id: str) -> str:
        """
        Get category for an event, using cache if available.
        Falls back to 'general' if not found.
        """
        return self._cache.get(event_id, "general")
    
    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._loaded = False


# Global cache instance - loaded once per newsletter run
_category_cache = CategoryCache()


def get_category_for_event(event_id: str) -> str:
    """Get category for an event from cache (O(1) lookup after batch load)."""
    return _category_cache.get(event_id)


def load_posts() -> List[Dict[str, Any]]:
    """Load events from all_posts.json"""
    with open("all_posts.json", "r", encoding="utf-8") as f:
        return json.load(f)


def clear_user_interactions(user_id: str):
    """Clear existing interactions for a user (fresh start)"""
    try:
        supabase.table("interactions").delete().eq("user_id", user_id).execute()
        print(f"  Cleared previous interactions for user {user_id}")
    except Exception as e:
        print(f"  Warning: Could not clear interactions: {e}")


def send_phase1_random_newsletter(user: Dict, posts: List[Dict]) -> List[str]:
    """Phase 1: Send 9 random events for initial discovery"""
    # Select 9 random events
    sample = random.sample(posts, min(9, len(posts)))
    
    events = []
    sent_ids = []
    for post in sample:
        event_id = post.get("id")
        category = get_category_for_event(event_id)
        
        event = {
            "event_id": event_id,
            "id": event_id,
            "title": post.get("caption", "")[:80].split('\n')[0] or "Event",
            "description": post.get("caption", "")[:200],
            "category": category,
            "timestamp": post.get("timestamp"),
            "media_url": post.get("media_url"),
            "permalink": post.get("permalink"),
        }
        events.append(event)
        sent_ids.append(event_id)
    
    # Generate and send email
    html = generate_personalized_email(user, events, "https://connect3-newsletter.vercel.app/feedback")
    subject = f"Phase 1: Discover 9 Events - Tell Us What You Like!"
    
    send_email(user["email"], subject, html)
    return sent_ids


def get_user_preferred_categories(user_id: str) -> List[str]:
    """Get user's top 3 liked categories based on their interactions"""
    resp = supabase.table("interactions").select("event_id, interaction_type").eq("user_id", user_id).execute()
    
    interactions = resp.data or []
    category_scores: Counter = Counter()
    
    for interaction in interactions:
        event_id = interaction.get("event_id")
        action = interaction.get("interaction_type", "like")
        
        if event_id:
            category = get_category_for_event(event_id)
            if action == "like":
                category_scores[category] += 1
            elif action == "dislike":
                category_scores[category] -= 0.5
    
    top_cats = [cat for cat, score in category_scores.most_common(3) if score > 0]
    
    # Fill with defaults if needed
    defaults = ["tech_innovation", "career_networking", "academic_workshops"]
    while len(top_cats) < 3:
        for d in defaults:
            if d not in top_cats:
                top_cats.append(d)
                break
        if len(top_cats) >= 3:
            break
    
    return top_cats[:3]


def get_events_by_category(posts: List[Dict], category: str, exclude_ids: set, limit: int) -> List[Dict]:
    """Get events matching a specific category"""
    matching = []
    for post in posts:
        event_id = post.get("id")
        if event_id in exclude_ids:
            continue
        
        cat = get_category_for_event(event_id)
        if cat == category:
            event = {
                "event_id": event_id,
                "id": event_id,
                "title": post.get("caption", "")[:80].split('\n')[0] or "Event",
                "description": post.get("caption", "")[:200],
                "category": cat,
                "timestamp": post.get("timestamp"),
                "media_url": post.get("media_url"),
            }
            matching.append(event)
            exclude_ids.add(event_id)
            
            if len(matching) >= limit:
                break
    
    return matching


def get_random_events(posts: List[Dict], exclude_ids: set, limit: int) -> List[Dict]:
    """Get random events for exploration"""
    available = [p for p in posts if p.get("id") not in exclude_ids]
    selected = random.sample(available, min(limit, len(available)))
    
    result = []
    for post in selected:
        event_id = post.get("id")
        event = {
            "event_id": event_id,
            "id": event_id,
            "title": post.get("caption", "")[:80].split('\n')[0] or "Event",
            "description": post.get("caption", "")[:200],
            "category": get_category_for_event(event_id),
            "timestamp": post.get("timestamp"),
        }
        exclude_ids.add(event_id)
        result.append(event)
    
    return result


def send_phase2_preference_newsletter(user: Dict, posts: List[Dict], phase1_ids: List[str], recommender: TwoTowerRecommender):
    """
    Phase 2: Send semantically personalized newsletter using Two-Tower recommender.
    
    Instead of simple category matching (13 buckets), this uses:
    - 1536-dimensional OpenAI embeddings for semantic understanding
    - User embedding computed from weighted Phase 1 interactions
    - Cosine similarity for finding related events
    - Built-in diversity penalty and recency scoring
    """
    user_id = user["id"]
    
    try:
        # Get recommendations using Two-Tower semantic matching
        # The recommender already:
        # - Computes user embedding from interactions (likes=1.0, clicks=0.5, dislikes=-0.5)
        # - Excludes events user already interacted with
        # - Applies recency weighting and diversity penalty
        recommendations = recommender.get_recommendations(user_id)
        
        if not recommendations:
            print(f"  Warning: No recommendations for user, falling back to random")
            exclude_ids = set(phase1_ids)
            recommendations = get_random_events(posts, exclude_ids, 9)
        
        print(f"  Two-Tower generated {len(recommendations)} recommendations")
        
        # Log top recommendation scores for debugging
        for i, rec in enumerate(recommendations[:3]):
            sim_score = rec.get('similarity_score', 0)
            category = rec.get('category', 'unknown')
            print(f"    #{i+1}: {category} (similarity: {sim_score:.3f})")
        
        # Format events for email template
        selected_events = []
        for rec in recommendations:
            event = {
                "event_id": rec.get("event_id"),
                "id": rec.get("event_id"),
                "title": rec.get("title", "Event"),
                "description": rec.get("caption", "")[:200],
                "category": rec.get("category"),
                "timestamp": rec.get("timestamp"),
                "media_url": rec.get("media_url", ""),
                "permalink": rec.get("permalink", ""),
                "reason": rec.get("reason", "Recommended for you"),
            }
            selected_events.append(event)
        
        # Send email
        html = generate_personalized_email(user, selected_events, "https://connect3-newsletter.vercel.app/feedback")
        subject = f"Phase 2: {len(selected_events)} Events Personalized For You!"
        
        send_email(user["email"], subject, html)
        
    except Exception as e:
        print(f"  Error in Two-Tower recommendations: {e}")
        # Fallback to random events
        exclude_ids = set(phase1_ids)
        selected_events = get_random_events(posts, exclude_ids, 9)
        html = generate_personalized_email(user, selected_events, "https://connect3-newsletter.vercel.app/feedback")
        subject = f"Phase 2: {len(selected_events)} Events For You!"
        send_email(user["email"], subject, html)


def run_two_phase_newsletter(delay_minutes: int = 5):
    """Run the complete two-phase newsletter flow"""
    posts = load_posts()
    print(f"Loaded {len(posts)} events from all_posts.json")
    
    # OPTIMIZATION: Batch-load all categories in a single DB query
    # This replaces N individual queries with 1 query
    event_ids = [p.get("id") for p in posts if p.get("id")]
    _category_cache.load_all(event_ids)
    
    # Get users
    users_resp = supabase.table("users").select("*").execute()
    ensure_ok(users_resp, action="select users")
    users = users_resp.data or []
    
    print(f"\n{'='*50}")
    print("PHASE 1: INITIAL DISCOVERY (Random Events)")
    print(f"{'='*50}")
    
    phase1_sent = {}
    
    for user in users:
        if not user.get("email"):
            continue
        
        print(f"\nProcessing: {user['email']}")
        
        # Clear previous interactions for fresh start
        clear_user_interactions(user["id"])
        
        # Send Phase 1
        sent_ids = send_phase1_random_newsletter(user, posts)
        phase1_sent[user["id"]] = sent_ids
        print(f"  Phase 1 sent: 9 random events")
    
    print(f"\n{'='*50}")
    print(f"WAITING {delay_minutes} MINUTES FOR USER TO SELECT PREFERENCES...")
    print(f"{'='*50}")
    print(f"(Click 'Interested' on events you like in the email!)")
    
    # Wait for user to interact
    for remaining in range(delay_minutes * 60, 0, -30):
        mins = remaining // 60
        secs = remaining % 60
        print(f"  Time remaining: {mins}m {secs}s")
        time.sleep(30)
    
    print(f"\n{'='*50}")
    print("PHASE 2: TWO-TOWER SEMANTIC RECOMMENDATIONS")
    print(f"{'='*50}")
    
    # Initialize Two-Tower recommender with NumPy-optimized vector search
    print("\nInitializing Two-Tower recommender...")
    recommender = TwoTowerRecommender()
    event_count = recommender.load_event_index()
    print(f"Loaded {event_count} event embeddings into vector index")
    
    for user in users:
        if not user.get("email"):
            continue
        
        print(f"\nProcessing: {user['email']}")
        phase1_ids = phase1_sent.get(user["id"], [])
        send_phase2_preference_newsletter(user, posts, phase1_ids, recommender)
        print(f"  Phase 2 sent: Semantically personalized events")
    
    print(f"\n{'='*50}")
    print("TWO-PHASE NEWSLETTER COMPLETE!")
    print(f"{'='*50}")


if __name__ == "__main__":
    # Run the two-phase flow with 5-minute delay
    run_two_phase_newsletter(delay_minutes=5)
