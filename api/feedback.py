"""
Vercel Serverless Function for email click tracking.

Stores the interaction then redirects to connect3.app.
Includes input validation, rate limiting, and time decay policy.

Time Decay Policy: Clicks on newsletters older than 15 days
do NOT update user preferences (prevents stale data from skewing recommendations).
"""

import json
import logging
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler
from threading import Lock
from urllib.parse import parse_qs, urlparse

from supabase import create_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s"
)
logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

# Time decay: clicks older than this many days don't affect preferences
PREFERENCE_DECAY_DAYS = 15

# Rate limiting settings
RATE_LIMIT_WINDOW_SECONDS = 60  # 1 minute window
RATE_LIMIT_MAX_REQUESTS = 30    # Max 30 requests per minute per user

# Validation patterns
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)
EVENT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')
CATEGORY_PATTERN = re.compile(r'^[a-z_]{1,50}$')
ACTION_WHITELIST = {'like', 'dislike', 'click'}

# Valid categories - matches CONNECT3_CATEGORIES from embeddings.py
# Note: 'general' is a fallback for validation, not a real event category
VALID_CATEGORIES = {
    'academic_workshops', 'career_networking', 'social_cultural',
    'sports_fitness', 'arts_music', 'tech_innovation',
    'volunteering_community', 'food_dining', 'travel_adventure',
    'health_wellness', 'entrepreneurship', 'environment_sustainability',
    'gaming_esports',
    'general',  # Fallback category for unclassified events
}

# Initialize Supabase client
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    logger.error("Supabase credentials not configured")

# =============================================================================
# Rate Limiting (In-Memory for Serverless)
# =============================================================================

# In-memory rate limit store (resets on cold start, which is acceptable for serverless)
_rate_limit_store: dict = defaultdict(list)
_rate_limit_lock = Lock()


def is_rate_limited(user_id: str) -> bool:
    """
    Check if a user has exceeded the rate limit.
    
    Uses a sliding window algorithm: tracks timestamps of requests
    within the window and rejects if count exceeds threshold.
    """
    if not user_id:
        return False
    
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    
    with _rate_limit_lock:
        # Clean old entries
        _rate_limit_store[user_id] = [
            ts for ts in _rate_limit_store[user_id] if ts > window_start
        ]
        
        # Check limit
        if len(_rate_limit_store[user_id]) >= RATE_LIMIT_MAX_REQUESTS:
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return True
        
        # Record this request
        _rate_limit_store[user_id].append(now)
        return False


# =============================================================================
# Input Validation
# =============================================================================

class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


def validate_user_id(user_id: str | None) -> str:
    """Validate and sanitize user ID (UUID format)."""
    if not user_id:
        raise ValidationError("Missing user_id parameter")
    
    user_id = user_id.strip()
    if not UUID_PATTERN.match(user_id):
        raise ValidationError(f"Invalid user_id format: {user_id[:20]}...")
    
    return user_id


def validate_event_id(event_id: str | None) -> str:
    """Validate and sanitize event ID."""
    if not event_id:
        raise ValidationError("Missing event_id parameter")
    
    event_id = event_id.strip()
    if not EVENT_ID_PATTERN.match(event_id):
        raise ValidationError(f"Invalid event_id format: {event_id[:20]}...")
    
    return event_id


def validate_category(category: str | None) -> str:
    """Validate and sanitize category."""
    if not category:
        return "general"
    
    category = category.strip().lower()
    if not CATEGORY_PATTERN.match(category):
        logger.warning(f"Invalid category format: {category[:20]}, defaulting to general")
        return "general"
    
    if category not in VALID_CATEGORIES:
        logger.warning(f"Unknown category: {category}, defaulting to general")
        return "general"
    
    return category


def validate_action(action: str | None) -> str:
    """Validate and sanitize action type."""
    if not action:
        return "like"
    
    action = action.strip().lower()
    if action not in ACTION_WHITELIST:
        logger.warning(f"Invalid action: {action}, defaulting to like")
        return "like"
    
    return action


def validate_timestamp(timestamp: str | None) -> str | None:
    """Validate ISO timestamp format."""
    if not timestamp:
        return None
    
    try:
        # Attempt to parse - this validates format
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return timestamp
    except (ValueError, AttributeError):
        logger.warning(f"Invalid timestamp format: {timestamp[:30]}")
        return None


# =============================================================================
# Business Logic
# =============================================================================

def is_within_decay_window(email_sent_at: str | None) -> bool:
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


def store_interaction(user_id: str, event_id: str, action: str) -> bool:
    """
    Store or update an interaction in the database.
    Returns True if successful, False otherwise.
    """
    if not supabase:
        logger.error("Supabase client not initialized - check SUPABASE_URL and SUPABASE_SERVICE_KEY env vars")
        return False
    
    try:
        logger.info(f"Attempting to store interaction: user={user_id[:8]}..., event={event_id}, action={action}")
        
        # Check for existing interaction (prevent duplicates)
        existing = (
            supabase.table('interactions')
            .select('id, interaction_type')
            .eq('user_id', user_id)
            .eq('event_id', event_id)
            .limit(1)
            .execute()
        )
        
        if existing.data:
            # Update existing interaction if action changed
            if existing.data[0].get('interaction_type') != action:
                result = supabase.table('interactions').update({
                    'interaction_type': action
                }).eq('id', existing.data[0]['id']).execute()
                logger.info(f"Updated interaction: user={user_id[:8]}..., event={event_id}, action={action}, result={result}")
        else:
            # Insert new interaction
            result = supabase.table('interactions').insert({
                'user_id': user_id,
                'event_id': event_id,
                'interaction_type': action
            }).execute()
            logger.info(f"Created interaction: user={user_id[:8]}..., event={event_id}, action={action}, result_data={result.data}")
        
        return True
    except Exception as e:
        logger.error(f"Error storing interaction: {type(e).__name__}: {e}")
        return False


def update_preferences(user_id: str, category: str, action: str) -> None:
    """Update user preferences based on interaction."""
    if not supabase or category == 'general':
        return
    
    try:
        # Uniform baseline: 1/13 ≈ 0.077
        UNIFORM_BASELINE = 1.0 / 13.0
        SCORE_INCREMENT = 0.05
        
        prefs = (
            supabase.table('user_preferences')
            .select('*')
            .eq('user_id', user_id)
            .limit(1)
            .execute()
        )
        
        if prefs.data:
            current_score = prefs.data[0].get(category, UNIFORM_BASELINE)
            if action == 'like':
                new_score = min(1.0, current_score + SCORE_INCREMENT)
            else:
                new_score = max(0.0, current_score - SCORE_INCREMENT)
            
            supabase.table('user_preferences').update({
                category: new_score
            }).eq('user_id', user_id).execute()
            logger.debug(f"Updated preference: {category} = {new_score:.3f}")
        else:
            # New user: start with uniform baseline, adjust for action
            initial_score = (
                UNIFORM_BASELINE + 0.1 if action == 'like' 
                else max(0.0, UNIFORM_BASELINE - SCORE_INCREMENT)
            )
            supabase.table('user_preferences').insert({
                'user_id': user_id,
                category: initial_score
            }).execute()
            logger.info(f"Created preferences for user {user_id[:8]}...")
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")


# =============================================================================
# HTTP Handler
# =============================================================================

class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler."""
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info("%s - %s", self.address_string(), format % args)
    
    def send_error_response(self, status_code: int, message: str) -> None:
        """Send a JSON error response."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'error': message}).encode())
    
    def send_redirect(self, url: str) -> None:
        """Send a redirect response."""
        self.send_response(302)
        self.send_header('Location', url)
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests for feedback tracking."""
        try:
            # Parse query parameters
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            
            # Extract and validate parameters
            try:
                user_id = validate_user_id(params.get('uid', [None])[0])
                event_id = validate_event_id(params.get('eid', [None])[0])
                category = validate_category(params.get('cat', ['general'])[0])
                action = validate_action(params.get('action', ['like'])[0])
                email_sent_at = validate_timestamp(params.get('sent', [None])[0])
            except ValidationError as e:
                logger.warning(f"Validation error: {e}")
                self.send_redirect('https://connect3.app?error=invalid_params')
                return
            
            # Rate limiting check
            if is_rate_limited(user_id):
                self.send_error_response(429, "Too many requests. Please try again later.")
                return
            
            # Store the interaction
            store_interaction(user_id, event_id, action)
            
            # Update preferences if within decay window
            if is_within_decay_window(email_sent_at):
                update_preferences(user_id, category, action)
            else:
                logger.info(f"Skipping preference update: email older than {PREFERENCE_DECAY_DAYS} days")
            
            # Redirect to success page
            self.send_redirect('https://connect3.app')
            
        except Exception as e:
            logger.exception(f"Unexpected error in feedback handler: {e}")
            self.send_redirect('https://connect3.app?error=server_error')
