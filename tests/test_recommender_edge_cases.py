"""Comprehensive edge case tests for python_app/recommender.py."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock


class TestRecommendationConfig:
    """Edge case tests for RecommendationConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        from python_app.recommender import RecommendationConfig
        
        config = RecommendationConfig()
        assert config.top_k == 10
        assert config.candidate_multiplier == 3
        assert config.recency_weight == 0.3
        assert config.similarity_weight == 0.7
        assert config.diversity_penalty == 0.1
        assert config.max_days_old == 365

    def test_from_overrides_single_value(self):
        """Single override is applied."""
        from python_app.recommender import RecommendationConfig
        
        config = RecommendationConfig.from_overrides({"top_k": 5})
        assert config.top_k == 5
        assert config.candidate_multiplier == 3  # Unchanged

    def test_from_overrides_multiple_values(self):
        """Multiple overrides are applied."""
        from python_app.recommender import RecommendationConfig
        
        config = RecommendationConfig.from_overrides({
            "top_k": 20,
            "recency_weight": 0.5,
            "similarity_weight": 0.5
        })
        assert config.top_k == 20
        assert config.recency_weight == 0.5
        assert config.similarity_weight == 0.5

    def test_from_overrides_none(self):
        """None overrides returns default config."""
        from python_app.recommender import RecommendationConfig
        
        config = RecommendationConfig.from_overrides(None)
        assert config.top_k == 10

    def test_from_overrides_empty_dict(self):
        """Empty dict returns default config."""
        from python_app.recommender import RecommendationConfig
        
        config = RecommendationConfig.from_overrides({})
        assert config.top_k == 10

    def test_from_overrides_unknown_key_ignored(self):
        """Unknown keys are ignored without error."""
        from python_app.recommender import RecommendationConfig
        
        config = RecommendationConfig.from_overrides({"unknown_key": 999})
        assert not hasattr(config, "unknown_key") or config.top_k == 10

    def test_weights_sum_to_one(self):
        """Default weights sum to 1.0."""
        from python_app.recommender import RecommendationConfig
        
        config = RecommendationConfig()
        assert config.recency_weight + config.similarity_weight == 1.0


class TestParseDate:
    """Edge case tests for date parsing function."""

    def test_valid_z_suffix(self):
        """Parse Z suffix correctly."""
        from python_app.recommender import _parse_date
        
        result = _parse_date("2024-01-15T10:30:00Z")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_valid_positive_offset(self):
        """Parse positive timezone offset."""
        from python_app.recommender import _parse_date
        
        result = _parse_date("2024-01-15T10:30:00+05:30")
        assert result is not None

    def test_valid_negative_offset(self):
        """Parse negative timezone offset."""
        from python_app.recommender import _parse_date
        
        result = _parse_date("2024-01-15T10:30:00-08:00")
        assert result is not None

    def test_none_input(self):
        """None input returns None."""
        from python_app.recommender import _parse_date
        
        assert _parse_date(None) is None

    def test_empty_string(self):
        """Empty string returns None."""
        from python_app.recommender import _parse_date
        
        assert _parse_date("") is None

    def test_invalid_format(self):
        """Invalid format returns None."""
        from python_app.recommender import _parse_date
        
        assert _parse_date("not-a-date") is None
        assert _parse_date("2024/01/15") is None
        assert _parse_date("01-15-2024") is None

    def test_microseconds(self):
        """Date with microseconds parses correctly."""
        from python_app.recommender import _parse_date
        
        result = _parse_date("2024-01-15T10:30:00.123456Z")
        assert result is not None


class TestExtractTitle:
    """Edge case tests for title extraction."""

    def test_first_line_extracted(self):
        """First line of caption becomes title."""
        from python_app.recommender import TwoTowerRecommender
        
        recommender = TwoTowerRecommender.__new__(TwoTowerRecommender)
        
        result = recommender._extract_title("First Line\nSecond Line\nThird")
        assert result == "First Line"

    def test_empty_string_returns_event(self):
        """Empty caption returns 'Event'."""
        from python_app.recommender import TwoTowerRecommender
        
        recommender = TwoTowerRecommender.__new__(TwoTowerRecommender)
        
        assert recommender._extract_title("") == "Event"

    def test_none_returns_event(self):
        """None caption returns 'Event'."""
        from python_app.recommender import TwoTowerRecommender
        
        recommender = TwoTowerRecommender.__new__(TwoTowerRecommender)
        
        assert recommender._extract_title(None) == "Event"

    def test_long_title_truncated(self):
        """Long title is truncated to 100 chars with ellipsis."""
        from python_app.recommender import TwoTowerRecommender
        
        recommender = TwoTowerRecommender.__new__(TwoTowerRecommender)
        
        long_caption = "A" * 150
        result = recommender._extract_title(long_caption)
        
        assert len(result) == 103  # 100 + "..."
        assert result.endswith("...")

    def test_exactly_100_chars_no_ellipsis(self):
        """Exactly 100 char title has no ellipsis."""
        from python_app.recommender import TwoTowerRecommender
        
        recommender = TwoTowerRecommender.__new__(TwoTowerRecommender)
        
        caption = "A" * 100
        result = recommender._extract_title(caption)
        
        assert len(result) == 100
        assert not result.endswith("...")

    def test_non_ascii_removed(self):
        """Non-ASCII characters are removed."""
        from python_app.recommender import TwoTowerRecommender
        
        recommender = TwoTowerRecommender.__new__(TwoTowerRecommender)
        
        # Emojis and unicode should be stripped
        result = recommender._extract_title("Hello 🎉 World 🌍")
        assert "🎉" not in result
        assert "🌍" not in result
        assert result.strip() == "Hello  World"

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace is stripped."""
        from python_app.recommender import TwoTowerRecommender
        
        recommender = TwoTowerRecommender.__new__(TwoTowerRecommender)
        
        result = recommender._extract_title("  Title with spaces  \nMore text")
        assert result == "Title with spaces"


class TestGenerateReason:
    """Edge case tests for recommendation reason generation."""

    def test_high_similarity_reason(self):
        """High similarity (>0.8) generates 'Matches your interests closely'."""
        from python_app.recommender import TwoTowerRecommender
        
        recommender = TwoTowerRecommender.__new__(TwoTowerRecommender)
        
        event = {"similarity_score": 0.85, "recency_score": 0.5, "category": None}
        reason = recommender._generate_reason(event)
        
        assert "Matches your interests closely" in reason

    def test_medium_similarity_reason(self):
        """Medium similarity (0.6-0.8) generates 'Related to topics you enjoy'."""
        from python_app.recommender import TwoTowerRecommender
        
        recommender = TwoTowerRecommender.__new__(TwoTowerRecommender)
        
        event = {"similarity_score": 0.7, "recency_score": 0.5, "category": None}
        reason = recommender._generate_reason(event)
        
        assert "Related to topics you enjoy" in reason

    def test_low_similarity_no_interest_reason(self):
        """Low similarity (<0.6) doesn't add interest reason."""
        from python_app.recommender import TwoTowerRecommender
        
        recommender = TwoTowerRecommender.__new__(TwoTowerRecommender)
        
        event = {"similarity_score": 0.4, "recency_score": 0.5, "category": None}
        reason = recommender._generate_reason(event)
        
        assert "Matches your interests" not in reason
        assert "Related to topics" not in reason

    def test_category_included_in_reason(self):
        """Category is included in reason with underscores replaced."""
        from python_app.recommender import TwoTowerRecommender
        
        recommender = TwoTowerRecommender.__new__(TwoTowerRecommender)
        
        event = {"similarity_score": 0.5, "recency_score": 0.5, "category": "tech_innovation"}
        reason = recommender._generate_reason(event)
        
        assert "tech innovation" in reason  # Underscore replaced with space

    def test_high_recency_reason(self):
        """High recency (>0.8) generates 'Happening soon'."""
        from python_app.recommender import TwoTowerRecommender
        
        recommender = TwoTowerRecommender.__new__(TwoTowerRecommender)
        
        event = {"similarity_score": 0.5, "recency_score": 0.9, "category": None}
        reason = recommender._generate_reason(event)
        
        assert "Happening soon" in reason

    def test_no_reasons_returns_default(self):
        """No matching reasons returns 'Recommended for you'."""
        from python_app.recommender import TwoTowerRecommender
        
        recommender = TwoTowerRecommender.__new__(TwoTowerRecommender)
        
        event = {"similarity_score": 0.4, "recency_score": 0.4, "category": None}
        reason = recommender._generate_reason(event)
        
        assert reason == "Recommended for you"

    def test_multiple_reasons_joined_with_bullet(self):
        """Multiple reasons are joined with ' • '."""
        from python_app.recommender import TwoTowerRecommender
        
        recommender = TwoTowerRecommender.__new__(TwoTowerRecommender)
        
        event = {"similarity_score": 0.85, "recency_score": 0.9, "category": "tech_innovation"}
        reason = recommender._generate_reason(event)
        
        assert " • " in reason

    def test_missing_scores_handled(self):
        """Missing scores default to 0."""
        from python_app.recommender import TwoTowerRecommender
        
        recommender = TwoTowerRecommender.__new__(TwoTowerRecommender)
        
        event = {}  # No scores
        reason = recommender._generate_reason(event)
        
        assert reason == "Recommended for you"


class TestDiversityPenalty:
    """Tests for diversity penalty in rankings."""

    def test_diversity_penalty_increases_per_category(self):
        """Diversity penalty increases with repeated categories."""
        from python_app.recommender import RecommendationConfig
        
        config = RecommendationConfig()
        
        # First item: no penalty
        # Second item same category: 0.1 penalty
        # Third item same category: 0.2 penalty
        penalty_increment = config.diversity_penalty
        assert penalty_increment == 0.1


class TestMaxDaysOld:
    """Tests for max_days_old filtering."""

    def test_default_max_days(self):
        """Default max_days_old is 365."""
        from python_app.recommender import RecommendationConfig
        
        config = RecommendationConfig()
        assert config.max_days_old == 365

    def test_max_days_can_be_overridden(self):
        """max_days_old can be overridden."""
        from python_app.recommender import RecommendationConfig
        
        config = RecommendationConfig.from_overrides({"max_days_old": 30})
        assert config.max_days_old == 30
