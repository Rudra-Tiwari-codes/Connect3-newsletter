"""Centralized category definitions for Connect3.

This module provides the single source of truth for event categories
used throughout the application. All category-related constants should
be imported from here to ensure consistency.
"""

from typing import FrozenSet, List

# The 13 official Connect3 event categories
# These are used for classification, embeddings, and user preferences
CONNECT3_CATEGORIES: List[str] = [
    "academic_workshops",
    "arts_music",
    "career_networking",
    "entrepreneurship",
    "environment_sustainability",
    "food_dining",
    "gaming_esports",
    "health_wellness",
    "social_cultural",
    "sports_fitness",
    "tech_innovation",
    "travel_adventure",
    "volunteering_community",
]

# Set version for O(1) lookups
CONNECT3_CATEGORIES_SET: FrozenSet[str] = frozenset(CONNECT3_CATEGORIES)

# Number of categories (used for uniform baseline calculations)
NUM_CATEGORIES: int = len(CONNECT3_CATEGORIES)

# Uniform baseline score for new users: 1/13 ≈ 0.077
UNIFORM_BASELINE: float = 1.0 / NUM_CATEGORIES

# Categories valid for API validation (includes 'general' fallback)
VALID_API_CATEGORIES: FrozenSet[str] = CONNECT3_CATEGORIES_SET | {"general"}

# Mapping from category to descriptive text for embedding generation
CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "academic_workshops": "academic workshops, revision sessions, study groups",
    "arts_music": "arts, music, creative performances, exhibitions",
    "career_networking": "career development, networking, industry connections",
    "entrepreneurship": "startups, entrepreneurship, business",
    "environment_sustainability": "environment, sustainability, green initiatives, climate",
    "food_dining": "food, dining, cooking, culinary experiences",
    "gaming_esports": "gaming, esports, video games, tournaments",
    "health_wellness": "health, wellness, mental health, self-care",
    "social_cultural": "social events, parties, cultural activities",
    "sports_fitness": "sports, fitness, physical activities",
    "tech_innovation": "technology, AI, machine learning, coding",
    "travel_adventure": "travel, adventure, outdoor activities, exploration",
    "volunteering_community": "volunteering, community service, charity events",
}
