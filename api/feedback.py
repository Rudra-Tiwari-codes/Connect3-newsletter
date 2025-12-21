"""
Vercel Serverless Function for email click tracking.
Stores the interaction then redirects to connect3.app

Time Decay Policy: Clicks on newsletters older than 15 days
do NOT update user preferences (prevents stale data from skewing recommendations).
"""
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from datetime import datetime, timezone, timedelta
import json
import os

# Initialize Supabase client
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

# Time decay: clicks older than this many days don't affect preferences
PREFERENCE_DECAY_DAYS = 15

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def is_within_decay_window(email_sent_at: str) -> bool:
    """
    Check if the email was sent within the decay window.
    Returns True if interaction should update preferences, False otherwise.
    """
    if not email_sent_at:
        return True  # No timestamp = allow update (backwards compatibility)
    
    try:
        sent_date = datetime.fromisoformat(email_sent_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age = now - sent_date
        return age <= timedelta(days=PREFERENCE_DECAY_DAYS)
    except Exception:
        return True  # Parse error = allow update (fail-safe)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse query parameters
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        
        user_id = params.get('uid', [None])[0]
        event_id = params.get('eid', [None])[0]
        category = params.get('cat', ['general'])[0]
        action = params.get('action', ['like'])[0]
        email_sent_at = params.get('sent', [None])[0]  # Timestamp when email was sent
        
        # Store the interaction if we have required data
        if supabase and user_id and event_id:
            try:
                # Check for existing interaction (prevent duplicates)
                existing = supabase.table('interactions').select('id, interaction_type').eq('user_id', user_id).eq('event_id', event_id).limit(1).execute()
                
                if existing.data:
                    # Update existing interaction if action changed
                    if existing.data[0].get('interaction_type') != action:
                        supabase.table('interactions').update({
                            'interaction_type': action
                        }).eq('id', existing.data[0]['id']).execute()
                else:
                    # Insert new interaction (no duplicate exists)
                    supabase.table('interactions').insert({
                        'user_id': user_id,
                        'event_id': event_id,
                        'interaction_type': action
                    }).execute()
                
                # TIME DECAY CHECK: Only update preferences if within 15-day window
                should_update_prefs = is_within_decay_window(email_sent_at)
                
                if should_update_prefs and category and category != 'general':
                    try:
                        # Uniform baseline: 1/13 ≈ 0.077
                        UNIFORM_BASELINE = 1.0 / 13.0
                        prefs = supabase.table('user_preferences').select('*').eq('user_id', user_id).limit(1).execute()
                        
                        if prefs.data:
                            current_score = prefs.data[0].get(category, UNIFORM_BASELINE)
                            # Adjust by 0.05 increments (smaller steps for probability-like scores)
                            new_score = min(1.0, current_score + 0.05) if action == 'like' else max(0.0, current_score - 0.05)
                            supabase.table('user_preferences').update({category: new_score}).eq('user_id', user_id).execute()
                        else:
                            # New user: start with uniform baseline, bump liked category
                            new_prefs = {'user_id': user_id, category: UNIFORM_BASELINE + 0.1 if action == 'like' else max(0.0, UNIFORM_BASELINE - 0.05)}
                            supabase.table('user_preferences').insert(new_prefs).execute()
                    except Exception as e:
                        print(f"Error updating preferences: {e}")
                elif not should_update_prefs:
                    print(f"Skipping preference update: email older than {PREFERENCE_DECAY_DAYS} days")
                        
            except Exception as e:
                print(f"Error storing interaction: {e}")
        
        # Redirect to clean connect3.app URL
        self.send_response(302)
        self.send_header('Location', 'https://connect3.app')
        self.end_headers()
        return
