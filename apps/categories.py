"""Centralized category definitions for Connect3.

This module provides the single source of truth for event categories
used throughout the application. All category-related constants should
be imported from here to ensure consistency.
"""

from typing import FrozenSet, List

# The official Connect3 event categories
# These are used for user preferences
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
    "recruitment",
]

# Set version for O(1) lookups
CONNECT3_CATEGORIES_SET: FrozenSet[str] = frozenset(CONNECT3_CATEGORIES)

# Number of categories (used for uniform baseline calculations)
NUM_CATEGORIES: int = len(CONNECT3_CATEGORIES)

# Uniform baseline score for new users: 1/NUM_CATEGORIES
UNIFORM_BASELINE: float = 1.0 / NUM_CATEGORIES

# Categories valid for API validation (includes 'general' fallback)
VALID_API_CATEGORIES: FrozenSet[str] = CONNECT3_CATEGORIES_SET | {"general"}
