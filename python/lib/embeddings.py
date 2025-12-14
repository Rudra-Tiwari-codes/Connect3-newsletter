"""
Two-Tower Embedding System for Connect3 Event Recommendations

This implements a simplified two-tower architecture:
- Event Tower: Converts event text → embedding using OpenAI embeddings
- User Tower: Converts user preferences → embedding

For MVP, we use OpenAI's text-embedding-3-small which is:
- Fast and cheap ($0.02 per 1M tokens)
- 1536 dimensions (can be reduced)
- Good semantic understanding
"""
import os
import re
import json
import math
from typing import List, Optional, Dict, Any, Literal
from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

from .supabase_client import supabase
from .config import EMBEDDING_CONFIG

# Load environment variables
load_dotenv()

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OpenAI API key. Set OPENAI_API_KEY environment variable.")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Event categories for Connect3 (derived from DSCubed events)
CONNECT3_CATEGORIES = [
    "tech_workshop",      # AI, ML, coding workshops
    "career_networking",  # Industry panels, networking events
    "hackathon",          # Datathons, coding competitions
    "social_event",       # Bar nights, board games, social mixers
    "academic_revision",  # SWOTVAC sessions, exam prep
    "recruitment",        # Club recruitment, AGMs
    "industry_talk",      # Company presentations, guest speakers
    "sports_recreation",  # Sports day, physical activities
    "entrepreneurship",   # Startup events, founder talks
    "community_service",  # Volunteering, community events
]

Connect3Category = Literal[
    "tech_workshop", "career_networking", "hackathon", "social_event",
    "academic_revision", "recruitment", "industry_talk", "sports_recreation",
    "entrepreneurship", "community_service"
]

# Embedding dimensions
EMBEDDING_DIM = EMBEDDING_CONFIG.EMBEDDING_DIM


@dataclass
class EventEmbedding:
    event_id: str
    embedding: List[float]
    category: Optional[str]
    created_at: str


@dataclass
class UserEmbedding:
    user_id: str
    embedding: List[float]
    updated_at: str


class EmbeddingService:
    """Two-tower embedding service for events and users"""
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        response = openai_client.embeddings.create(
            model=EMBEDDING_CONFIG.MODEL,
            input=text,
            encoding_format="float"
        )
        return response.data[0].embedding
    
    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch"""
        response = openai_client.embeddings.create(
            model=EMBEDDING_CONFIG.MODEL,
            input=texts,
            encoding_format="float"
        )
        return [d.embedding for d in response.data]
    
    def embed_event(self, event: Dict[str, Any]) -> EventEmbedding:
        """
        EVENT TOWER: Convert event to embedding
        Combines title, description, and inferred category
        """
        # Create rich text representation for embedding
        caption = event.get("caption", "")
        event_text = self._prepare_event_text(caption)
        
        embedding = self.generate_embedding(event_text)
        
        # Classify event category using the caption
        category = self.classify_event_category(caption)
        
        return EventEmbedding(
            event_id=event["id"],
            embedding=embedding,
            category=category,
            created_at=event.get("timestamp", datetime.now().isoformat())
        )
    
    def _prepare_event_text(self, caption: str) -> str:
        """Prepare event text for embedding"""
        # Clean up Instagram caption for embedding
        # Remove hashtags but keep the words
        clean_text = re.sub(r"#(\w+)", r"\1", caption)
        
        # Remove emoji
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002600-\U000026FF"  # misc symbols
            "\U00002700-\U000027BF"  # dingbats
            "]+",
            flags=re.UNICODE
        )
        clean_text = emoji_pattern.sub("", clean_text)
        
        # Collapse whitespace
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        
        # Truncate to reasonable length
        return clean_text[:8000]
    
    def classify_event_category(self, caption: str) -> Optional[str]:
        """Classify event into Connect3 category using AI"""
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"Classify this university club event into ONE of these categories:\n"
                                   f"{', '.join(CONNECT3_CATEGORIES)}\n\n"
                                   f"Respond with ONLY the category name, nothing else."
                    },
                    {"role": "user", "content": caption[:2000]}
                ],
                temperature=0.1,
                max_tokens=50
            )
            
            category = response.choices[0].message.content.strip().lower()
            
            if category in CONNECT3_CATEGORIES:
                return category
            
            return None
        except Exception as e:
            print(f"Error classifying event: {e}")
            return None
    
    def embed_user(self, user_id: str) -> UserEmbedding:
        """
        USER TOWER: Convert user preferences to embedding
        
        For users with interaction history: Average their interacted event embeddings
        For new users: Generate from declared preferences
        """
        # Check if user has interaction history
        result = supabase.table("feedback_logs").select("event_id, action").eq("user_id", user_id).execute()
        interactions = result.data or []
        
        if interactions:
            # User has history - use weighted average of interacted events
            return self._embed_user_from_history(user_id, interactions)
        else:
            # Cold start - use declared preferences
            return self._embed_user_from_preferences(user_id)
    
    def _embed_user_from_history(
        self, 
        user_id: str, 
        interactions: List[Dict[str, Any]]
    ) -> UserEmbedding:
        """Embed user from interaction history (weighted average)"""
        # Fetch event embeddings for interacted events
        event_ids = [i["event_id"] for i in interactions]
        
        result = supabase.table("event_embeddings").select("event_id, embedding").in_("event_id", event_ids).execute()
        event_embeddings = result.data or []
        
        if not event_embeddings:
            return self._embed_user_from_preferences(user_id)
        
        # Weight by action type
        weights = {
            "like": 1.0,
            "click": 0.5,
            "dislike": -0.5
        }
        
        # Compute weighted average
        embedding = [0.0] * EMBEDDING_DIM
        total_weight = 0.0
        
        for interaction in interactions:
            event_emb = next(
                (e for e in event_embeddings if e["event_id"] == interaction["event_id"]),
                None
            )
            if event_emb and event_emb.get("embedding"):
                weight = weights.get(interaction["action"], 0)
                emb_vector = (
                    json.loads(event_emb["embedding"]) 
                    if isinstance(event_emb["embedding"], str) 
                    else event_emb["embedding"]
                )
                
                for i in range(EMBEDDING_DIM):
                    embedding[i] += emb_vector[i] * weight
                total_weight += abs(weight)
        
        # Normalize
        if total_weight > 0:
            embedding = [e / total_weight for e in embedding]
        
        return UserEmbedding(
            user_id=user_id,
            embedding=embedding,
            updated_at=datetime.now().isoformat()
        )
    
    def _embed_user_from_preferences(self, user_id: str) -> UserEmbedding:
        """Embed user from declared preferences (cold start)"""
        # Fetch user preferences
        result = supabase.table("user_preferences").select("*").eq("user_id", user_id).single().execute()
        preferences = result.data
        
        # Build a text representation of preferences
        preferences_text = "University student interested in: "
        
        if preferences:
            interests = []
            
            # Map preference scores to interests
            pref_mapping = {
                "tech_innovation": "technology, AI, machine learning, coding",
                "career_networking": "career development, networking, industry connections",
                "academic_workshops": "academic workshops, revision sessions, study groups",
                "social_cultural": "social events, parties, cultural activities",
                "entrepreneurship": "startups, entrepreneurship, business",
                "sports_fitness": "sports, fitness, physical activities"
            }
            
            for key, description in pref_mapping.items():
                score = preferences.get(key, 0)
                if score and score > 0.6:
                    interests.append(description)
            
            if interests:
                preferences_text += ", ".join(interests)
            else:
                preferences_text += "general university events"
        else:
            preferences_text += "general university events, student activities"
        
        embedding = self.generate_embedding(preferences_text)
        
        return UserEmbedding(
            user_id=user_id,
            embedding=embedding,
            updated_at=datetime.now().isoformat()
        )
    
    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two embeddings"""
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        
        if norm_a * norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    def find_similar_events(
        self,
        user_embedding: List[float],
        top_n: int = 10,
        exclude_event_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Find top-N similar events for a user embedding"""
        exclude_event_ids = exclude_event_ids or []
        
        # Fetch all event embeddings
        result = supabase.table("event_embeddings").select("event_id, embedding").execute()
        event_embeddings = result.data or []
        
        if not event_embeddings:
            return []
        
        # Compute similarities
        similarities = []
        for event in event_embeddings:
            if event["event_id"] in exclude_event_ids:
                continue
            
            emb_vector = (
                json.loads(event["embedding"])
                if isinstance(event["embedding"], str)
                else event["embedding"]
            )
            
            similarities.append({
                "event_id": event["event_id"],
                "similarity": self.cosine_similarity(user_embedding, emb_vector)
            })
        
        # Sort by similarity and return top N
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        return similarities[:top_n]


# Singleton instance
embedding_service = EmbeddingService()
