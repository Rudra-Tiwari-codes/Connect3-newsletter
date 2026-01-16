"""Tests for python_app/constants.py centralized configuration."""

import pytest


class TestConstants:
    """Tests for centralized constants."""

    def test_scoring_weights_are_positive(self):
        """Scoring weights should be positive numbers."""
        from python_app.constants import (
            CLUSTER_MATCH_WEIGHT,
            MAX_URGENCY_SCORE,
            DECAY_HALF_LIFE_DAYS,
        )
        
        assert CLUSTER_MATCH_WEIGHT > 0
        assert MAX_URGENCY_SCORE > 0
        assert DECAY_HALF_LIFE_DAYS > 0

    def test_category_configuration(self):
        """Category configuration should be consistent."""
        from python_app.constants import (
            NUM_CATEGORIES,
            DEFAULT_CATEGORY_SCORE,
            PREFERENCE_UNIFORM_BASELINE,
        )
        
        assert NUM_CATEGORIES == 13
        assert DEFAULT_CATEGORY_SCORE == pytest.approx(1.0 / 13, rel=1e-3)
        assert PREFERENCE_UNIFORM_BASELINE == DEFAULT_CATEGORY_SCORE

    def test_rate_limiting_config(self):
        """Rate limiting should have reasonable defaults."""
        from python_app.constants import (
            RATE_LIMIT_WINDOW_SECONDS,
            RATE_LIMIT_MAX_REQUESTS,
        )
        
        assert RATE_LIMIT_WINDOW_SECONDS == 60
        assert RATE_LIMIT_MAX_REQUESTS == 30

    def test_phase2_distribution_sums_to_nine(self):
        """Phase 2 event distribution should sum to 9."""
        from python_app.constants import PHASE2_DISTRIBUTION, DEFAULT_PHASE2_EVENTS
        
        total = sum(PHASE2_DISTRIBUTION.values())
        assert total == DEFAULT_PHASE2_EVENTS

    def test_embedding_dimension(self):
        """Embedding dimension should match OpenAI model."""
        from python_app.constants import EMBEDDING_DIM
        
        assert EMBEDDING_DIM == 1536  # text-embedding-3-small


class TestUrlHelpers:
    """Tests for URL helper functions."""

    def test_get_site_url_default(self, monkeypatch):
        """Returns default when no env vars set."""
        from python_app.constants import get_site_url
        
        monkeypatch.delenv("NEXT_PUBLIC_SITE_URL", raising=False)
        monkeypatch.delenv("NEXT_PUBLIC_APP_URL", raising=False)
        
        # Reload module to pick up env changes
        import importlib
        import python_app.constants
        importlib.reload(python_app.constants)
        from python_app.constants import get_site_url
        
        url = get_site_url()
        assert "connect3" in url.lower()

    def test_get_feedback_url_has_path(self, monkeypatch):
        """Feedback URL includes /feedback path."""
        from python_app.constants import get_feedback_url
        
        url = get_feedback_url()
        assert url.endswith("/feedback")
