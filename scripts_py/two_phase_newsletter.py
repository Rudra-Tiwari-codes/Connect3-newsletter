"""
Two-Phase Newsletter Delivery System

Phase 1: Send 9 random events for discovery
Phase 2: After 5 minutes, send preference-based newsletter (3-3-1-2 distribution)

Optimized: Uses batch category fetching to reduce DB calls from N to 1.
"""

import json
import random
import sys
import time
from datetime import datetime, timezone
from collections import Counter
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path so we can import python_app from any directory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python_app.email_sender import send_email
from python_app.email_templates import generate_personalized_email
from python_app.logger import get_logger
from python_app.supabase_client import supabase, ensure_ok

logger = get_logger(__name__)


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
            logger.info(f"CategoryCache: Loaded {len(self._cache)} categories in 1 query")
        except Exception as e:
            logger.warning(f"Failed to batch load categories: {e}")
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


def is_new_recipient(user: Dict[str, Any]) -> bool:
    """Determine if a user should receive the two-phase onboarding flow."""
    is_new_flag = user.get("is_new_recipient")
    first_sent_at = user.get("first_newsletter_sent_at")
    return bool(is_new_flag) or not first_sent_at


def mark_user_onboarded(user: Dict[str, Any]) -> None:
    """Mark a user as no longer new after the initial newsletter."""
    payload: Dict[str, Any] = {"is_new_recipient": False}
    if not user.get("first_newsletter_sent_at"):
        payload["first_newsletter_sent_at"] = datetime.now(timezone.utc).isoformat()
    try:
        resp = supabase.table("users").update(payload).eq("id", user["id"]).execute()
        ensure_ok(resp, action="update user onboarding status")
    except Exception as e:
        logger.warning(f"Failed to update onboarding status for user {user.get('id')}: {e}")


def clear_user_interactions(user_id: str):
    """Clear existing interactions for a user (fresh start)"""
    try:
        supabase.table("interactions").delete().eq("user_id", user_id).execute()
        logger.info(f"Cleared previous interactions for user {user_id}")
    except Exception as e:
        logger.warning(f"Could not clear interactions: {e}")


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


def get_exploration_events(posts: List[Dict], exclude_ids: set, preferred_categories: List[str], limit: int) -> List[Dict]:
    """
    Get events from categories NOT in user's preferences for discovery/exploration.
    This helps users discover new interests outside their current preferences.
    """
    # Find events in non-preferred categories
    exploration_candidates = []
    for post in posts:
        event_id = post.get("id")
        if event_id in exclude_ids:
            continue
        
        category = get_category_for_event(event_id)
        # Only include if NOT in user's preferred categories
        if category not in preferred_categories and category != "general":
            exploration_candidates.append((post, category))
    
    # Randomly select from exploration candidates
    if not exploration_candidates:
        # Fallback: if no exploration events, just get any random events
        available = [p for p in posts if p.get("id") not in exclude_ids]
        selected = random.sample(available, min(limit, len(available)))
        exploration_candidates = [(p, get_category_for_event(p.get("id"))) for p in selected]
    else:
        exploration_candidates = random.sample(
            exploration_candidates, 
            min(limit, len(exploration_candidates))
        )
    
    result = []
    for post, category in exploration_candidates:
        event_id = post.get("id")
        event = {
            "event_id": event_id,
            "id": event_id,
            "title": post.get("caption", "")[:80].split('\n')[0] or "Event",
            "description": post.get("caption", "")[:200],
            "category": category,
            "timestamp": post.get("timestamp"),
            "is_exploration": True,  # Mark as exploration event
        }
        exclude_ids.add(event_id)
        result.append(event)
    
    return result


def store_user_top_categories(user_id: str, categories: List[str]) -> None:
    """
    Store user's top categories in the users table for future reference.
    This allows tracking preference evolution over time.
    """
    try:
        supabase.table("users").update({
            "top_categories": categories
        }).eq("id", user_id).execute()
        logger.info(f"Stored top categories: {categories}")
    except Exception as e:
        logger.warning(f"Could not store top categories: {e}")


def send_phase2_preference_newsletter(user: Dict, posts: List[Dict], phase1_ids: List[str]):
    """Phase 2: Send preference-based newsletter (3-3-1-2 distribution)"""
    user_id = user["id"]
    categories = get_user_preferred_categories(user_id)
    logger.info(f"User's preferred categories: {categories}")
    
    # Store user's top categories for future reference
    store_user_top_categories(user_id, categories)
    
    exclude_ids = set(phase1_ids)  # Don't repeat Phase 1 events
    selected_events = []
    
    # 3 from category 1
    cat1_events = get_events_by_category(posts, categories[0], exclude_ids, 3)
    selected_events.extend(cat1_events)
    logger.debug(f"{len(cat1_events)} from {categories[0]}")
    
    # 3 from category 2
    cat2_events = get_events_by_category(posts, categories[1], exclude_ids, 3)
    selected_events.extend(cat2_events)
    logger.debug(f"{len(cat2_events)} from {categories[1]}")
    
    # 1 from category 3
    cat3_events = get_events_by_category(posts, categories[2], exclude_ids, 1)
    selected_events.extend(cat3_events)
    logger.debug(f"{len(cat3_events)} from {categories[2]}")
    
    # 2 exploration events from NON-preferred categories
    exploration_events = get_exploration_events(posts, exclude_ids, categories, 2)
    selected_events.extend(exploration_events)
    exploration_cats = [e.get('category', 'unknown') for e in exploration_events]
    logger.debug(f"{len(exploration_events)} exploration from: {exploration_cats}")
    
    # Send email
    html = generate_personalized_email(user, selected_events, "https://connect3-newsletter.vercel.app/feedback")
    subject = f"Phase 2: {len(selected_events)} Events Curated Just For You!"
    
    send_email(user["email"], subject, html)


def run_two_phase_newsletter(delay_minutes: int = 5):
    """Run the complete two-phase newsletter flow"""
    posts = load_posts()
    logger.info(f"Loaded {len(posts)} events from all_posts.json")
    
    # OPTIMIZATION: Batch-load all categories in a single DB query
    # This replaces N individual queries with 1 query
    event_ids = [p.get("id") for p in posts if p.get("id")]
    _category_cache.load_all(event_ids)
    
    # Get users
    users_resp = supabase.table("users").select(
        "id,email,name,is_new_recipient,first_newsletter_sent_at,is_unsubscribed"
    ).execute()
    ensure_ok(users_resp, action="select users")
    users = users_resp.data or []

    new_users = []
    returning_users = []
    for user in users:
        if not user.get("email"):
            continue
        if user.get("is_unsubscribed"):
            logger.info(f"Skipping unsubscribed user: {user.get('email')}")
            continue
        if is_new_recipient(user):
            new_users.append(user)
        else:
            returning_users.append(user)

    if returning_users:
        logger.info("="*50)
        logger.info("PREFERENCE-BASED NEWSLETTER (RETURNING USERS)")
        logger.info("="*50)

        for user in returning_users:
            logger.info(f"Processing: {user['email']}")
            send_phase2_preference_newsletter(user, posts, [])
            logger.info("Sent: Personalized events")

    phase1_sent = {}
    if new_users:
        logger.info("="*50)
        logger.info("PHASE 1: INITIAL DISCOVERY (NEW USERS)")
        logger.info("="*50)

        for user in new_users:
            logger.info(f"Processing: {user['email']}")

            # Clear previous interactions for fresh start
            clear_user_interactions(user["id"])

            # Send Phase 1
            sent_ids = send_phase1_random_newsletter(user, posts)
            phase1_sent[user["id"]] = sent_ids
            mark_user_onboarded(user)
            logger.info("Phase 1 sent: 9 random events")

        logger.info("="*50)
        logger.info(f"WAITING UP TO {delay_minutes} MINUTES...")
        logger.info("Scanning for interactions every 10 seconds to send Phase 2 immediately.")
        logger.info("="*50)

        # Track who has been sent Phase 2 to avoid double sending
        phase2_sent_users = set()
        
        # Poll loop
        poll_interval = 10
        max_duration = delay_minutes * 60
        start_time = time.time()
        
        while (time.time() - start_time) < max_duration:
            # Check for interactions for ALL pending users
            pending_users = [u for u in new_users if u["id"] not in phase2_sent_users]
            if not pending_users:
                logger.info("All users have interacted! Finishing early.")
                break
                
            elapsed = int(time.time() - start_time)
            logger.debug(f"[{elapsed}s / {max_duration}s] Checking interactions for {len(pending_users)} users...")
            
            for user in pending_users:
                # Check if user has ANY interactions since Phase 1 started
                # We can optimize this by checking timestamps, but counting is safe enough for this scale
                resp = supabase.table("interactions").select("count", count="exact").eq("user_id", user["id"]).execute()
                
                # If they have interacted (count > 0), trigger Phase 2 NOW
                if resp.count and resp.count > 0:
                    logger.info(f">>> INTERACTION DETECTED for {user['email']}!")
                    phase1_ids = phase1_sent.get(user["id"], [])
                    send_phase2_preference_newsletter(user, posts, phase1_ids)
                    logger.info("Phase 2 sent: Personalized events (Instant)")
                    phase2_sent_users.add(user["id"])
            
            time.sleep(poll_interval)

        logger.info("="*50)
        logger.info("TIMEOUT REACHED - SENDING DEFAULTS TO REMAINING USERS")
        logger.info("="*50)

        # Process anyone left who hasn't interacted
        remaining_users = [u for u in new_users if u["id"] not in phase2_sent_users]
        for user in remaining_users:
            logger.info(f"Processing (Default): {user['email']}")
            phase1_ids = phase1_sent.get(user["id"], [])
            send_phase2_preference_newsletter(user, posts, phase1_ids)
            logger.info("Phase 2 sent: Default Recommendation events")
    
    logger.info("="*50)
    logger.info("TWO-PHASE NEWSLETTER COMPLETE!")
    logger.info("="*50)


if __name__ == "__main__":
    # Run the two-phase flow with 5-minute delay
    run_two_phase_newsletter(delay_minutes=5)
