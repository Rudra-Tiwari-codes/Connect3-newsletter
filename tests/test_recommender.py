"""Tests for python_app/recommender.py TwoTowerRecommender."""

import pytest


class MockVectorIndex:
    """Mock VectorIndex for testing."""
    
    def __init__(self):
        self._items = []
    
    def size(self):
        return len(self._items)
    
    def clear(self):
        self._items = []
    
    def add(self, id, embedding, metadata):
        self._items.append({"id": id, "embedding": embedding, "metadata": metadata})
    
    def search(self, query, top_k=10, exclude_ids=None):
        exclude = exclude_ids or set()
        results = []
        for item in self._items:
            if item["id"] not in exclude:
                results.append({
                    "id": item["id"],
                    "score": 0.9,
                    "metadata": item["metadata"]
                })
        return results[:top_k]


def test_recommendation_config_defaults():
    """Test that RecommendationConfig has sensible defaults."""
    from python_app.recommender import RecommendationConfig
    
    config = RecommendationConfig()
    assert config.top_k == 10
    assert config.candidate_multiplier == 3
    assert 0 <= config.similarity_weight <= 1
    assert 0 <= config.recency_weight <= 1


def test_recommendation_config_from_overrides():
    """Test that overrides are applied correctly."""
    from python_app.recommender import RecommendationConfig
    
    config = RecommendationConfig.from_overrides({"top_k": 5})
    assert config.top_k == 5


def test_parse_date_valid():
    """Test date parsing with valid ISO format."""
    from python_app.recommender import _parse_date
    
    result = _parse_date("2024-01-15T10:30:00Z")
    assert result is not None
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 15


def test_parse_date_invalid():
    """Test date parsing returns None for invalid format."""
    from python_app.recommender import _parse_date
    
    assert _parse_date(None) is None
    assert _parse_date("") is None
    assert _parse_date("not-a-date") is None


def test_extract_title():
    """Test title extraction from caption."""
    from python_app.recommender import TwoTowerRecommender
    
    recommender = TwoTowerRecommender.__new__(TwoTowerRecommender)
    
    # First line becomes title
    assert recommender._extract_title("Hello World\nMore text") == "Hello World"
    
    # Empty returns "Event"
    assert recommender._extract_title("") == "Event"
    assert recommender._extract_title(None) == "Event"


def test_generate_reason_high_similarity():
    """Test reason generation for high similarity events."""
    from python_app.recommender import TwoTowerRecommender
    
    recommender = TwoTowerRecommender.__new__(TwoTowerRecommender)
    
    event = {"similarity_score": 0.85, "recency_score": 0.5, "category": "tech_innovation"}
    reason = recommender._generate_reason(event)
    
    assert "Matches your interests closely" in reason
