"""
Two-Phase Newsletter Delivery System

Phase 1: Send 9 random events for discovery
Phase 2: Send preference-based newsletter for every subsequent iteration

Optimized: Uses batch category fetching to reduce DB calls from N to 1.
"""

import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path so we can import python_app from any directory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python_app.subscribers import fetch_subscriber_emails
from python_app.email_sender import send_email
from python_app.email_templates import generate_personalized_email, format_category
from python_app.logger import get_logger, setup_logging
from python_app.supabase_client import supabase, ensure_ok
from python_app.config import get_env

logger = get_logger(__name__)

# Base URL for feedback links (configurable for local dev)
SITE_URL = get_env("NEXT_PUBLIC_SITE_URL") or get_env("NEXT_PUBLIC_APP_URL") or "https://connect3-newsletter.vercel.app"
FEEDBACK_BASE_URL = f"{SITE_URL.rstrip('/')}/feedback"
DEFAULT_PHASE2_TOTAL = 9
MAX_EVENT_LOOKAHEAD_DAYS = 30

CATEGORY_COLUMNS = [
    "academic_workshops", "arts_music", "career_networking", 
    "entrepreneurship", "environment_sustainability", "food_dining", 
    "gaming_esports", "health_wellness", "social_cultural", 
    "sports_fitness", "tech_innovation", "travel_adventure", 
    "volunteering_community", "recruitment"
]

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

def log_probability_distribution(user_id: str) -> None:
    """Log user preference distribution as a simple bar chart."""
    try:
        resp = (
            supabase.table("user_preferences")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        ensure_ok(resp, action="select user_preferences")
        if not resp.data:
            logger.info(f"No preference distribution for user {user_id[:8]}...")
            return
        prefs = resp.data[0]
        logger.info(f"Printing probability distribution for user {user_id[:8]}...")
        bar_scale = 20
        for cat in CATEGORY_COLUMNS:
            try:
                score = float(prefs.get(cat, 0.0))
            except (TypeError, ValueError):
                score = 0.0
            bar = "#" * max(0, int(round(score * bar_scale)))
            logger.info(f"{cat.ljust(24)} {bar}")
    except Exception as exc:
        logger.warning(f"Failed to print probability distribution for user {user_id[:8]}...: {exc}")

def _parse_event_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None

def _event_window_from_post(post: Dict[str, Any]) -> tuple[Optional[datetime], Optional[datetime]]:
    end_dt = None
    for key in ("end", "end_time", "end_date"):
        end_dt = _parse_event_datetime(post.get(key))
        if end_dt:
            break

    start_dt = None
    for key in ("start", "start_time", "start_date", "event_date", "timestamp", "date", "created_at"):
        start_dt = _parse_event_datetime(post.get(key))
        if start_dt:
            break

    return start_dt, end_dt

def _is_event_within_window(post: Dict[str, Any], now: datetime, max_days: int) -> bool:
    start_dt, end_dt = _event_window_from_post(post)
    if not end_dt and not start_dt:
        return False
    if end_dt is None:
        end_dt = start_dt
    if end_dt is None:
        return False
    if end_dt < now:
        return False
    delta_days = (end_dt - now).total_seconds() / 86400
    return 0 <= delta_days <= max_days

def load_posts() -> List[Dict[str, Any]]:
    """Load events from Supabase."""
    resp = supabase.table("events").select("*").execute()
    ensure_ok(resp, action="select events")
    posts = resp.data or []
    now = datetime.now(timezone.utc)
    filtered: List[Dict[str, Any]] = []
    for post in posts:
        if post.get("id") is not None:
            post["id"] = str(post["id"])
        attendable = post.get("is_attendable")
        if attendable is None:
            attendable = post.get("isAttendable")
        if not attendable:
            continue
        if _is_event_within_window(post, now, MAX_EVENT_LOOKAHEAD_DAYS):
            filtered.append(post)
    return filtered

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
        resp = supabase.table("profiles").update(payload).eq("id", user["id"]).execute()
        ensure_ok(resp, action="update profile onboarding status")
    except Exception as e:
        logger.warning(f"Failed to update onboarding status for user {user.get('id')}: {e}")

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

def _annotate_group_header(
    events: List[Dict[str, Any]],
    title: str,
    *,
    action_label: Optional[str] = None,
    action_category: Optional[str] = None,
) -> None:
    if not events:
        return
    events[0]["group_title"] = title
    if action_label and action_category:
        event_id = events[0].get("event_id") or events[0].get("id")
        events[0]["group_action_label"] = action_label
        events[0]["group_action_event_id"] = event_id
        events[0]["group_action_category"] = action_category

def _resolve_category(post: Dict[str, Any]) -> str:
    return post.get("category") or "general"

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
    log_probability_distribution(user["id"])
    html = generate_personalized_email(user, events, FEEDBACK_BASE_URL)
    subject = f"Phase 1: Discover 9 Events - Tell Us What You Like!"
    
    try:
        logger.info(f"Sending Phase 1 email to {user['email']}")
        send_email(user["email"], subject, html)
        log_email_sent(user["id"], sent_ids, status="sent")
    except Exception as e:
        log_email_sent(user["id"], sent_ids, status="failed", error_message=str(e))
        raise
    
    return sent_ids

def get_user_preferred_categories(user_id: str) -> List[str]:
    """
    Get user's top 2 preferred categories based on user_preferences scores.
    
    Uses the stored preference scores (updated by clicks via feedback.py)
    instead of counting raw interactions. This provides proper personalization.
    """
    # Fetch user's preference scores from user_preferences table
    resp = supabase.table("user_preferences").select("*").eq("user_id", user_id).limit(1).execute()
    
    if resp.data and len(resp.data) > 0:
        prefs = resp.data[0]
        # Build list of (category, score) tuples
        category_scores = []
        for cat in CATEGORY_COLUMNS:
            score = prefs.get(cat, 0.077)  # Default uniform baseline
            category_scores.append((cat, score))
        
        # Sort by score descending and get top 2
        category_scores.sort(key=lambda x: x[1], reverse=True)
        top_cats = [cat for cat, score in category_scores[:2] if score > 0]
        
        # Log for debugging
        logger.info(f"User {user_id[:8]}... preference scores: {category_scores[:5]}")
        
        if len(top_cats) >= 2:
            return top_cats[:2]
    else:
        logger.warning(f"No user_preferences found for user {user_id}, using defaults")
    
    # Fallback to defaults if no preferences or not enough data
    defaults = ["tech_innovation", "career_networking"]
    return defaults[:2]

def get_events_by_category(posts: List[Dict], category: str, exclude_ids: set, limit: int) -> List[Dict]:
    """Get events matching a specific category"""
    candidates = []
    for post in posts:
        event_id = post.get("id")
        if event_id in exclude_ids:
            continue
        
        cat = _resolve_category(post)
        if cat == category:
            candidates.append(post)

    if not candidates or limit <= 0:
        return []

    selected = random.sample(candidates, min(limit, len(candidates)))
    result = []
    for post in selected:
        event_id = post.get("id")
        event = build_event_from_post(post, category)
        exclude_ids.add(event_id)
        result.append(event)
    return result

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
        supabase.table("profiles").update({
            "top_categories": categories
        }).eq("id", user_id).execute()
        logger.info(f"Stored top categories: {categories}")
    except Exception as e:
        logger.warning(f"Could not store top categories: {e}")


def send_phase2_preference_newsletter(user: Dict, posts: List[Dict], phase1_ids: List[str]):
    """Phase 2: Send preference-based newsletter with top-2 + random diversity mix."""
    user_id = user["id"]
    categories = get_user_preferred_categories(user_id)
    logger.info(f"User's preferred categories: {categories}")
    
    # Store user's top categories for future reference
    store_user_top_categories(user_id, categories)
    
    exclude_ids = set(phase1_ids)  # Don't repeat Phase 1 events
    # Up to 3 from category 1
    cat1_events = get_events_by_category(posts, categories[0], exclude_ids, 3)
    logger.debug(f"{len(cat1_events)} from {categories[0]}")
    
    # Up to 3 from category 2
    cat2_events = get_events_by_category(posts, categories[1], exclude_ids, 3)
    logger.debug(f"{len(cat2_events)} from {categories[1]}")
    
    # Fill remaining slots with random valid events for diversity
    remaining = DEFAULT_PHASE2_TOTAL - (len(cat1_events) + len(cat2_events))
    exploration_events = get_exploration_events(posts, exclude_ids, categories, remaining)
    exploration_cats = [e.get('category', 'unknown') for e in exploration_events]
    logger.debug(f"{len(exploration_events)} exploration from: {exploration_cats}")

    _annotate_group_header(
        cat1_events,
        format_category(categories[0]),
        action_label="See less of this category",
        action_category=categories[0],
    )
    _annotate_group_header(
        cat2_events,
        format_category(categories[1]),
        action_label="See less of this category",
        action_category=categories[1],
    )
    _annotate_group_header(exploration_events, "Some more events")

    selected_events = cat1_events + cat2_events + exploration_events

    # Send email
    log_probability_distribution(user_id)
    html = generate_personalized_email(user, selected_events, FEEDBACK_BASE_URL)
    subject = f"Phase 2: {len(selected_events)} Events Curated Just For You!"
    
    sent_ids = [e.get("event_id") or e.get("id") for e in selected_events]
    try:
        logger.info(f"Sending Phase 2 email to {user['email']}")
        send_email(user["email"], subject, html)
        log_email_sent(user["id"], sent_ids, status="sent")
    except Exception as e:
        log_email_sent(user["id"], sent_ids, status="failed", error_message=str(e))
        raise
"""
Function to run the newsletter flow
"""
def run_two_phase_newsletter():
    posts = load_posts()
    logger.info(f"Loaded {len(posts)} events from Supabase")
    
    # Get users
    users_resp = supabase.table("profiles").select(
        "id,first_name,last_name,is_new_recipient,first_newsletter_sent_at,is_unsubscribed"
    ).execute()
    ensure_ok(users_resp, action="select profiles")
    users = users_resp.data or []

    subscriber_emails = fetch_subscriber_emails([u.get("id") for u in users if u.get("id")])
    logger.info(f"Loaded subscriber emails: {len(subscriber_emails)} of {len(users)} users")
    for user in users:
        user_id = user.get("id")
        subscriber_email = subscriber_emails.get(str(user_id)) if user_id else None
        if subscriber_email:
            user["email"] = subscriber_email
        first_name = (user.get("first_name") or "").strip()
        last_name = (user.get("last_name") or "").strip()
        full_name = f"{first_name} {last_name}".strip()
        if full_name:
            user["name"] = full_name

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

        logger.info("="*50)
        logger.info("SKIPPING PHASE 2 WAIT (CRON MODE)")
        logger.info("New users will receive Phase 2 on the next scheduled run.")
        logger.info("="*50)
        logger.info("TWO-PHASE NEWSLETTER COMPLETE!")
        logger.info("="*50)
        return
    
    logger.info("="*50)
    logger.info("TWO-PHASE NEWSLETTER COMPLETE!")
    logger.info("="*50)

if __name__ == "__main__":
    setup_logging()
    
    # Silence verbose HTTP client logs (httpx, httpcore, hpack)
    import logging as _logging
    for noisy_logger in ['httpx', 'httpcore', 'hpack', 'h2', 'urllib3']:
        _logging.getLogger(noisy_logger).setLevel(_logging.WARNING)
    
    run_two_phase_newsletter()
