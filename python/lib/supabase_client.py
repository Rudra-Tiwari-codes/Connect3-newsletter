"""
Supabase client and database models for Connect3
"""
import os
from typing import Optional, List, Literal
from dataclasses import dataclass, field
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Get Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(
        "Missing Supabase environment variables. "
        "Please set SUPABASE_URL and SUPABASE_SERVICE_KEY (or SUPABASE_SECRET_KEY)"
    )

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# Database models
@dataclass
class Event:
    id: str
    title: str
    event_date: str
    created_at: str
    updated_at: str
    description: Optional[str] = None
    location: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    source_url: Optional[str] = None


@dataclass
class User:
    id: str
    email: str
    created_at: str
    updated_at: str
    name: Optional[str] = None
    pca_cluster_id: Optional[int] = None


@dataclass
class UserPreferences:
    user_id: str
    updated_at: str
    academic_workshops: float = 0.5
    career_networking: float = 0.5
    social_cultural: float = 0.5
    sports_fitness: float = 0.5
    arts_music: float = 0.5
    tech_innovation: float = 0.5
    volunteering_community: float = 0.5
    food_dining: float = 0.5
    travel_adventure: float = 0.5
    health_wellness: float = 0.5
    entrepreneurship: float = 0.5
    environment_sustainability: float = 0.5
    gaming_esports: float = 0.5


@dataclass
class FeedbackLog:
    id: str
    user_id: str
    event_id: str
    action: Literal["like", "dislike", "click"]
    created_at: str


@dataclass
class RankedEvent(Event):
    score: float = 0.0
    cluster_match: float = 0.0
    urgency_score: float = 0.0


# Event categories
EVENT_CATEGORIES = [
    "academic_workshops",
    "career_networking",
    "social_cultural",
    "sports_fitness",
    "arts_music",
    "tech_innovation",
    "volunteering_community",
    "food_dining",
    "travel_adventure",
    "health_wellness",
    "entrepreneurship",
    "environment_sustainability",
    "gaming_esports",
]

EventCategory = Literal[
    "academic_workshops",
    "career_networking",
    "social_cultural",
    "sports_fitness",
    "arts_music",
    "tech_innovation",
    "volunteering_community",
    "food_dining",
    "travel_adventure",
    "health_wellness",
    "entrepreneurship",
    "environment_sustainability",
    "gaming_esports",
]

# Mapping preference columns to event categories
PREFERENCE_TO_CATEGORY = {cat: cat for cat in EVENT_CATEGORIES}
