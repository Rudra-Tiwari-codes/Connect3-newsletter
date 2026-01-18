"""
Two-Phase Newsletter Delivery System

Phase 1: Send 9 random events for discovery
Phase 2: After 5 minutes, send preference-based newsletter (3-3-1-2 distribution)

Optimized: Uses batch category fetching to reduce DB calls from N to 1.
"""

import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path so we can import python_app from any directory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python_app.email_sender import send_email
from python_app.email_templates import generate_personalized_email
from python_app.logger import get_logger, setup_logging
from python_app.supabase_client import supabase, ensure_ok
from python_app.config import get_env

logger = get_logger(__name__)

# Base URL for feedback links (configurable for local dev)
SITE_URL = get_env("NEXT_PUBLIC_SITE_URL") or get_env("NEXT_PUBLIC_APP_URL") or "https://connect3-newsletter.vercel.app"
FEEDBACK_BASE_URL = f"{SITE_URL.rstrip('/')}/feedback"
DEFAULT_PHASE2_TOTAL = 9
WAIT_FOR_INTERACTIONS_ENV = False


def log_email_sent(user_id: str, events_sent: List[str], status: str = "sent", error_message: str = None) -> None:
    """Log email delivery to email_logs table."""
    try:
        log_data = {
            "user_id": user_id,
            "status": status,
            "events_sent": events_sent,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        if error_message:
            log_data["error_message"] = error_message
        
        supabase.table("email_logs").insert(log_data).execute()
        logger.debug(f"Logged email: user={user_id[:8]}..., status={status}")
    except Exception as e:
        logger.warning(f"Failed to log email: {e}")


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
    """Load events from Supabase."""
    resp = supabase.table("events").select("*").execute()
    ensure_ok(resp, action="select events")
    posts = resp.data or []
    for post in posts:
        if post.get("id") is not None:
            post["id"] = str(post["id"])
    return posts


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


def build_event_from_post(
    post: Dict[str, Any],
    category: Optional[str],
    *,
    is_exploration: bool = False,
) -> Dict[str, Any]:
    event_id = post.get("id")
    caption = post.get("caption", "") or ""
    title = (
        post.get("title")
        or caption[:80].split("\n")[0]
        or "Event"
    )
    description = post.get("description") or caption[:200]
    timestamp = post.get("timestamp") or post.get("event_date") or post.get("date") or post.get("created_at")
    media_url = post.get("media_url") or post.get("image_url") or post.get("image")
    permalink = post.get("permalink") or post.get("source_url") or post.get("url")
    resolved_category = category or post.get("category") or "general"
    event = {
        "event_id": event_id,
        "id": event_id,
        "title": title,
        "description": description,
        "category": resolved_category,
        "timestamp": timestamp,
        "media_url": media_url,
        "permalink": permalink,
    }
    if is_exploration:
        event["is_exploration"] = True
    return event


def _resolve_category(post: Dict[str, Any]) -> str:
    post_category = post.get("category")
    if post_category:
        return post_category
    event_id = post.get("id")
    return get_category_for_event(event_id)


def send_phase1_random_newsletter(user: Dict, posts: List[Dict]) -> List[str]:
    """Phase 1: Send 9 random events for initial discovery"""
    # Select 9 random events
    sample = random.sample(posts, min(9, len(posts)))
    
    events = []
    sent_ids = []
    for post in sample:
        event_id = post.get("id")
        category = _resolve_category(post)

        events.append(build_event_from_post(post, category))
        sent_ids.append(event_id)
    
    # Generate and send email
    html = generate_personalized_email(user, events, FEEDBACK_BASE_URL)
    subject = f"Phase 1: Discover 9 Events - Tell Us What You Like!"
    
    try:
        send_email(user["email"], subject, html)
        log_email_sent(user["id"], sent_ids, status="sent")
    except Exception as e:
        log_email_sent(user["id"], sent_ids, status="failed", error_message=str(e))
        raise
    
    return sent_ids


def get_user_preferred_categories(user_id: str) -> List[str]:
    """
    Get user's top 3 preferred categories based on user_preferences scores.
    
    Uses the stored preference scores (updated by clicks via feedback.py)
    instead of counting raw interactions. This provides proper personalization.
    """
    # Category columns in user_preferences table
    CATEGORY_COLUMNS = [
        "tech_innovation", "career_networking", "academic_workshops",
        "social_cultural", "entrepreneurship", "sports_fitness",
        "arts_music", "volunteering_community", "food_dining",
        "travel_adventure", "health_wellness", "environment_sustainability",
        "gaming_esports"
    ]
    
    # Fetch user's preference scores from user_preferences table
    resp = supabase.table("user_preferences").select("*").eq("user_id", user_id).limit(1).execute()
    
    if resp.data and len(resp.data) > 0:
        prefs = resp.data[0]
        # Build list of (category, score) tuples
        category_scores = []
        for cat in CATEGORY_COLUMNS:
            score = prefs.get(cat, 0.077)  # Default uniform baseline
            category_scores.append((cat, score))
        
        # Sort by score descending and get top 3
        category_scores.sort(key=lambda x: x[1], reverse=True)
        top_cats = [cat for cat, score in category_scores[:3] if score > 0]
        
        # Log for debugging
        logger.info(f"User {user_id[:8]}... preference scores: {category_scores[:5]}")
        
        if len(top_cats) >= 3:
            return top_cats[:3]
    else:
        logger.warning(f"No user_preferences found for user {user_id}, using defaults")
    
    # Fallback to defaults if no preferences or not enough data
    defaults = ["tech_innovation", "career_networking", "academic_workshops"]
    return defaults[:3]


def get_events_by_category(posts: List[Dict], category: str, exclude_ids: set, limit: int) -> List[Dict]:
    """Get events matching a specific category"""
    matching = []
    for post in posts:
        event_id = post.get("id")
        if event_id in exclude_ids:
            continue
        
        cat = _resolve_category(post)
        if cat == category:
            matching.append(build_event_from_post(post, cat))
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
        
        category = _resolve_category(post)
        # Only include if NOT in user's preferred categories
        if category not in preferred_categories and category != "general":
            exploration_candidates.append((post, category))
    
    # Randomly select from exploration candidates
    if not exploration_candidates:
        # Fallback: if no exploration events, just get any random events
        available = [p for p in posts if p.get("id") not in exclude_ids]
        selected = random.sample(available, min(limit, len(available)))
        exploration_candidates = [(p, _resolve_category(p)) for p in selected]
    else:
        exploration_candidates = random.sample(
            exploration_candidates, 
            min(limit, len(exploration_candidates))
        )
    
    result = []
    for post, category in exploration_candidates:
        event_id = post.get("id")
        event = build_event_from_post(post, category, is_exploration=True)
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


def top_up_events(posts: List[Dict], exclude_ids: set, limit: int) -> List[Dict]:
    """Fill remaining slots with random events not already selected."""
    available = [p for p in posts if p.get("id") not in exclude_ids]
    if not available or limit <= 0:
        return []
    selected = random.sample(available, min(limit, len(available)))
    result = []
    for post in selected:
        event_id = post.get("id")
        category = _resolve_category(post)
        result.append(build_event_from_post(post, category))
        exclude_ids.add(event_id)
    return result


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

    if len(selected_events) < DEFAULT_PHASE2_TOTAL:
        remaining = DEFAULT_PHASE2_TOTAL - len(selected_events)
        top_ups = top_up_events(posts, exclude_ids, remaining)
        selected_events.extend(top_ups)
        logger.debug(f"{len(top_ups)} top-up events to reach {DEFAULT_PHASE2_TOTAL}")
    
    # Send email
    html = generate_personalized_email(user, selected_events, FEEDBACK_BASE_URL)
    subject = f"Phase 2: {len(selected_events)} Events Curated Just For You!"
    
    sent_ids = [e.get("event_id") or e.get("id") for e in selected_events]
    try:
        send_email(user["email"], subject, html)
        log_email_sent(user["id"], sent_ids, status="sent")
    except Exception as e:
        log_email_sent(user["id"], sent_ids, status="failed", error_message=str(e))
        raise


def run_two_phase_newsletter(delay_minutes: int = 5, wait_for_interactions: Optional[bool] = None):
    """Run the complete two-phase newsletter flow."""
    if wait_for_interactions is None:
        wait_for_interactions = WAIT_FOR_INTERACTIONS_ENV

    posts = load_posts()
    logger.info(f"Loaded {len(posts)} events from Supabase")
    
    # OPTIMIZATION: Batch-load all categories in a single DB query
    # This replaces N individual queries with 1 query
    if any(not p.get("category") for p in posts):
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
            try:
                send_phase2_preference_newsletter(user, posts, [])
                logger.info("Sent: Personalized events")
            except Exception as exc:
                logger.error(f"Failed to send personalized newsletter to {user['email']}: {exc}")

    phase1_sent = {}
    if new_users:
        logger.info("="*50)
        logger.info("PHASE 1: INITIAL DISCOVERY (NEW USERS)")
        logger.info("="*50)

        for user in new_users:
            logger.info(f"Processing: {user['email']}")

            # NOTE: We no longer clear interactions - they are valuable click data!
            # Old code deleted user clicks which broke interaction detection.

            # Send Phase 1
            try:
                sent_ids = send_phase1_random_newsletter(user, posts)
                phase1_sent[user["id"]] = sent_ids
                mark_user_onboarded(user)
                logger.info("Phase 1 sent: 9 random events")
            except Exception as exc:
                logger.error(f"Failed to send Phase 1 to {user['email']}: {exc}")

        if not wait_for_interactions:
            logger.info("="*50)
            logger.info("SKIPPING PHASE 2 WAIT (CRON MODE)")
            logger.info("New users will receive Phase 2 on the next scheduled run.")
            logger.info("="*50)
            logger.info("TWO-PHASE NEWSLETTER COMPLETE!")
            logger.info("="*50)
            return

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
                # Check if user has ANY interactions OR if their preferences have been updated
                # This handles both direct interactions and preference updates from clicks
                interaction_count = 0
                prefs_changed = False
                
                try:
                    # Check interactions table
                    resp = supabase.table("interactions").select("count", count="exact").eq("user_id", user["id"]).execute()
                    interaction_count = resp.count or 0
                    
                    # Also check if user_preferences has non-default scores (indicates clicks happened)
                    prefs_resp = supabase.table("user_preferences").select("*").eq("user_id", user["id"]).limit(1).execute()
                    if prefs_resp.data:
                        p = prefs_resp.data[0]
                        # Check if any score differs from baseline 0.077 by more than 0.01
                        for cat in ['tech_innovation', 'career_networking', 'academic_workshops', 'social_cultural', 
                                    'entrepreneurship', 'sports_fitness', 'arts_music', 'volunteering_community',
                                    'food_dining', 'travel_adventure', 'health_wellness', 'environment_sustainability', 'gaming_esports']:
                            if abs(p.get(cat, 0.077) - 0.077) > 0.01:
                                prefs_changed = True
                                break
                except Exception as e:
                    logger.warning(f"Error checking interactions: {e}")
                
                # If they have interacted OR preferences changed, trigger Phase 2 NOW
                if interaction_count > 0 or prefs_changed:
                    logger.info(f">>> INTERACTION DETECTED for {user['email']}! (interactions={interaction_count}, prefs_changed={prefs_changed})")
                    phase1_ids = phase1_sent.get(user["id"], [])
                    try:
                        send_phase2_preference_newsletter(user, posts, phase1_ids)
                        logger.info("Phase 2 sent: Personalized events (Instant)")
                        phase2_sent_users.add(user["id"])
                    except Exception as exc:
                        logger.error(f"Failed to send Phase 2 to {user['email']}: {exc}")
            
            time.sleep(poll_interval)

        logger.info("="*50)
        logger.info("TIMEOUT REACHED - SENDING DEFAULTS TO REMAINING USERS")
        logger.info("="*50)

        # Process anyone left who hasn't interacted
        remaining_users = [u for u in new_users if u["id"] not in phase2_sent_users]
        for user in remaining_users:
            logger.info(f"Processing (Default): {user['email']}")
            phase1_ids = phase1_sent.get(user["id"], [])
            try:
                send_phase2_preference_newsletter(user, posts, phase1_ids)
                logger.info("Phase 2 sent: Default Recommendation events")
            except Exception as exc:
                logger.error(f"Failed to send Phase 2 to {user['email']}: {exc}")
    
    logger.info("="*50)
    logger.info("TWO-PHASE NEWSLETTER COMPLETE!")
    logger.info("="*50)


if __name__ == "__main__":
    setup_logging()
    
    # Silence verbose HTTP client logs (httpx, httpcore, hpack)
    import logging as _logging
    for noisy_logger in ['httpx', 'httpcore', 'hpack', 'h2', 'urllib3']:
        _logging.getLogger(noisy_logger).setLevel(_logging.WARNING)
    
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--delay-minutes", type=int, default=5)
    parser.add_argument("--wait-for-interactions", action="store_true")
    parser.add_argument("--no-wait-for-interactions", action="store_true")
    args = parser.parse_args()

    wait_for_interactions = None
    if args.wait_for_interactions:
        wait_for_interactions = True
    if args.no_wait_for_interactions:
        wait_for_interactions = False

    # Run the flow; default mode does not wait unless explicitly set via CLI flags.
    run_two_phase_newsletter(
        delay_minutes=args.delay_minutes,
        wait_for_interactions=wait_for_interactions,
    )
