"""
Vercel Serverless Function for email click tracking.
Stores the interaction then redirects to connect3.app
"""
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json
import os

# Initialize Supabase client
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse query parameters
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        
        user_id = params.get('uid', [None])[0]
        event_id = params.get('eid', [None])[0]
        category = params.get('cat', ['general'])[0]
        action = params.get('action', ['like'])[0]
        
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
                
                # Update user preferences for the category
                if category and category != 'general':
                    try:
                        prefs = supabase.table('user_preferences').select('*').eq('user_id', user_id).limit(1).execute()
                        
                        if prefs.data:
                            current_score = prefs.data[0].get(category, 0.5)
                            new_score = min(1.0, current_score + 0.1) if action == 'like' else max(0.0, current_score - 0.1)
                            supabase.table('user_preferences').update({category: new_score}).eq('user_id', user_id).execute()
                        else:
                            new_prefs = {'user_id': user_id, category: 0.7 if action == 'like' else 0.3}
                            supabase.table('user_preferences').insert(new_prefs).execute()
                    except Exception as e:
                        print(f"Error updating preferences: {e}")
                        
            except Exception as e:
                print(f"Error storing interaction: {e}")
        
        # Redirect to clean connect3.app URL
        self.send_response(302)
        self.send_header('Location', 'https://connect3.app')
        self.end_headers()
        return
