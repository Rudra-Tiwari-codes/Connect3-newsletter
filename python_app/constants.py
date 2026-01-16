"""Centralized constants and configuration values for Connect3.

This module provides a single source of truth for all magic numbers and
configuration values used across the codebase.
"""

from .config import get_env

# =============================================================================
# Scoring & Recommendation Weights
# =============================================================================

# Event scoring weights
CLUSTER_MATCH_WEIGHT = 50  # Category preference multiplier
MAX_URGENCY_SCORE = 30     # Maximum urgency bonus for upcoming events

# Time decay configuration
DECAY_HALF_LIFE_DAYS = 30.0  # Interaction weight halves every 30 days

# =============================================================================
# Category Configuration
# =============================================================================

NUM_CATEGORIES = 13
DEFAULT_CATEGORY_SCORE = 1.0 / NUM_CATEGORIES  # ~0.077 (uniform probability)

# Preference score adjustments (from feedback.py)
PREFERENCE_SCORE_INCREMENT = 0.05  # How much each like/dislike changes score
PREFERENCE_UNIFORM_BASELINE = 1.0 / NUM_CATEGORIES

# =============================================================================
# Rate Limiting
# =============================================================================

RATE_LIMIT_WINDOW_SECONDS = 60  # 1 minute window
RATE_LIMIT_MAX_REQUESTS = 30    # Max requests per window per user

# =============================================================================
# Time Decay for Feedback
# =============================================================================

PREFERENCE_DECAY_DAYS = 15  # Clicks older than this don't update preferences

# =============================================================================
# Newsletter Configuration
# =============================================================================

DEFAULT_PHASE2_EVENTS = 9  # Total events in Phase 2 newsletter
PHASE2_DISTRIBUTION = {
    "top_category": 3,
    "second_category": 3,
    "third_category": 1,
    "exploration": 2,
}

# =============================================================================
# Embedding Configuration
# =============================================================================

EMBEDDING_DIM = 1536  # OpenAI text-embedding-3-small dimension

# =============================================================================
# Site URLs (with fallbacks)
# =============================================================================

def get_site_url() -> str:
    """Get the site URL from environment variables."""
    return (
        get_env("NEXT_PUBLIC_SITE_URL")
        or get_env("NEXT_PUBLIC_APP_URL")
        or "https://connect3-newsletter.vercel.app"
    )

def get_feedback_url() -> str:
    """Get the feedback endpoint URL."""
    return f"{get_site_url().rstrip('/')}/feedback"
