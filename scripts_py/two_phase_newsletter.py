"""
Two-Phase Newsletter Delivery System

Phase 1: Send 9 random events for discovery
Phase 2: After 5 minutes, send preference-based newsletter (3-3-1-2 distribution)
"""

import json
import random
import time
from collections import Counter
from typing import Dict, List, Any

from python_app.email_sender import send_email
from python_app.email_templates import generate_personalized_email
from python_app.supabase_client import supabase, ensure_ok


def load_posts() -> List[Dict[str, Any]]:
    """Load events from all_posts.json"""
    with open("all_posts.json", "r", encoding="utf-8") as f:
        return json.load(f)


def get_category_for_event(event_id: str) -> str:
    """Get category for an event from event_embeddings"""
    resp = supabase.table("event_embeddings").select("category").eq("event_id", event_id).limit(1).execute()
    if resp.data and resp.data[0].get("category"):
        return resp.data[0]["category"]
    return "general"


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


def send_phase2_preference_newsletter(user: Dict, posts: List[Dict], phase1_ids: List[str]):
    """Phase 2: Send preference-based newsletter (3-3-1-2 distribution)"""
    user_id = user["id"]
    categories = get_user_preferred_categories(user_id)
    print(f"  User's preferred categories: {categories}")
    
    exclude_ids = set(phase1_ids)  # Don't repeat Phase 1 events
    selected_events = []
    
    # 3 from category 1
    cat1_events = get_events_by_category(posts, categories[0], exclude_ids, 3)
    selected_events.extend(cat1_events)
    print(f"  - {len(cat1_events)} from {categories[0]}")
    
    # 3 from category 2
    cat2_events = get_events_by_category(posts, categories[1], exclude_ids, 3)
    selected_events.extend(cat2_events)
    print(f"  - {len(cat2_events)} from {categories[1]}")
    
    # 1 from category 3
    cat3_events = get_events_by_category(posts, categories[2], exclude_ids, 1)
    selected_events.extend(cat3_events)
    print(f"  - {len(cat3_events)} from {categories[2]}")
    
    # 2 random
    random_events = get_random_events(posts, exclude_ids, 2)
    selected_events.extend(random_events)
    print(f"  - {len(random_events)} random")
    
    # Send email
    html = generate_personalized_email(user, selected_events, "https://connect3-newsletter.vercel.app/feedback")
    subject = f"Phase 2: {len(selected_events)} Events Curated Just For You!"
    
    send_email(user["email"], subject, html)


def run_two_phase_newsletter(delay_minutes: int = 5):
    """Run the complete two-phase newsletter flow"""
    posts = load_posts()
    print(f"Loaded {len(posts)} events from all_posts.json")
    
    # Get users
    users_resp = supabase.table("users").select("*").execute()
    ensure_ok(users_resp, action="select users")
    users = users_resp.data or []
    
    print(f"\n{'='*50}")
    print("PHASE 1: INITIAL DISCOVERY")
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
    print("PHASE 2: PREFERENCE-BASED NEWSLETTER")
    print(f"{'='*50}")
    
    for user in users:
        if not user.get("email"):
            continue
        
        print(f"\nProcessing: {user['email']}")
        phase1_ids = phase1_sent.get(user["id"], [])
        send_phase2_preference_newsletter(user, posts, phase1_ids)
        print(f"  Phase 2 sent: Personalized events")
    
    print(f"\n{'='*50}")
    print("TWO-PHASE NEWSLETTER COMPLETE!")
    print(f"{'='*50}")


if __name__ == "__main__":
    # Run the two-phase flow with 5-minute delay
    run_two_phase_newsletter(delay_minutes=5)
