"""
Phase 2: Preference-Based Follow-up Newsletter

Sends a personalized email based on user's liked categories from interactions.
Distribution: 3 from cat1, 3 from cat2, 1 from cat3, 2 random = 9 events
"""

import json
import random
import time
from collections import Counter
from datetime import datetime, timezone
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


def get_user_preferred_categories(user_id: str) -> List[str]:
    """Get user's top 3 liked categories based on their interactions"""
    resp = supabase.table("interactions").select("event_id, interaction_type").eq("user_id", user_id).execute()
    ensure_ok(resp, action="select interactions")
    
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
    
    # Get top 3 categories
    top_categories = [cat for cat, score in category_scores.most_common(3) if score > 0]
    
    # If less than 3 categories, fill with defaults
    defaults = ["tech_innovation", "career_networking", "academic_workshops"]
    while len(top_categories) < 3:
        for default in defaults:
            if default not in top_categories:
                top_categories.append(default)
                break
        if len(top_categories) >= 3:
            break
    
    return top_categories[:3]


def get_events_by_category(posts: List[Dict], category: str, exclude_ids: set, limit: int) -> List[Dict]:
    """Get events matching a specific category"""
    matching = []
    for post in posts:
        event_id = post.get("id")
        if event_id in exclude_ids:
            continue
        
        # Get category from embeddings
        cat = get_category_for_event(event_id)
        if cat == category:
            post_with_meta = dict(post)
            post_with_meta["category"] = cat
            post_with_meta["event_id"] = event_id
            matching.append(post_with_meta)
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
        post_with_meta = dict(post)
        post_with_meta["event_id"] = post.get("id")
        post_with_meta["category"] = get_category_for_event(post.get("id"))
        exclude_ids.add(post.get("id"))
        result.append(post_with_meta)
    
    return result


def build_preference_based_email(user_id: str, posts: List[Dict]) -> List[Dict]:
    """
    Build 9-event list based on user preferences:
    - 3 from top category
    - 3 from second category
    - 1 from third category
    - 2 random for exploration
    """
    categories = get_user_preferred_categories(user_id)
    print(f"  User's preferred categories: {categories}")
    
    exclude_ids = set()
    selected_events = []
    
    # 3 from category 1
    cat1_events = get_events_by_category(posts, categories[0], exclude_ids, 3)
    selected_events.extend(cat1_events)
    print(f"  - {len(cat1_events)} events from {categories[0]}")
    
    # 3 from category 2
    cat2_events = get_events_by_category(posts, categories[1], exclude_ids, 3)
    selected_events.extend(cat2_events)
    print(f"  - {len(cat2_events)} events from {categories[1]}")
    
    # 1 from category 3
    cat3_events = get_events_by_category(posts, categories[2], exclude_ids, 1)
    selected_events.extend(cat3_events)
    print(f"  - {len(cat3_events)} events from {categories[2]}")
    
    # 2 random for exploration
    random_events = get_random_events(posts, exclude_ids, 2)
    selected_events.extend(random_events)
    print(f"  - {len(random_events)} random events for exploration")
    
    return selected_events


def send_preference_based_newsletter(user_id: str = None, delay_minutes: int = 0):
    """Send preference-based newsletter to a user or all users"""
    
    if delay_minutes > 0:
        print(f"Waiting {delay_minutes} minutes before sending...")
        time.sleep(delay_minutes * 60)
    
    posts = load_posts()
    print(f"Loaded {len(posts)} events from all_posts.json")
    
    # Get user(s)
    if user_id:
        users_resp = supabase.table("users").select("*").eq("id", user_id).execute()
    else:
        users_resp = supabase.table("users").select("*").execute()
    
    ensure_ok(users_resp, action="select users")
    users = users_resp.data or []
    print(f"Sending preference-based newsletter to {len(users)} user(s)")
    
    for user in users:
        uid = user.get("id")
        email = user.get("email")
        
        if not email:
            print(f"  Skipping user {uid} - no email")
            continue
        
        print(f"\nProcessing user: {email}")
        
        # Build personalized event list
        events = build_preference_based_email(uid, posts)
        
        if not events:
            print(f"  No events found for user {uid}")
            continue
        
        # Generate and send email
        html = generate_personalized_email(user, events, "https://connect3-newsletter.vercel.app/feedback")
        subject = f"🎯 Your Personalized Event Picks - {len(events)} Events Just For You!"
        
        try:
            send_email(email, subject, html)
            print(f"  ✓ Email sent successfully to {email}")
        except Exception as e:
            print(f"  ✗ Failed to send email: {e}")
    
    print("\n✓ Preference-based newsletter delivery complete!")


if __name__ == "__main__":
    # Run immediately (set delay_minutes=5 for 5-minute delay)
    send_preference_based_newsletter(delay_minutes=0)
