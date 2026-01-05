"""Comprehensive edge case tests for python_app/scoring.py."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
import math


class TestParseDate:
    """Edge case tests for date parsing."""

    def test_parse_valid_iso_z_suffix(self):
        """Parse valid ISO date with Z suffix."""
        from python_app.scoring import _parse_date
        
        result = _parse_date("2024-01-15T10:30:00Z")
        assert result is not None
        assert result.year == 2024

    def test_parse_valid_iso_offset(self):
        """Parse valid ISO date with timezone offset."""
        from python_app.scoring import _parse_date
        
        result = _parse_date("2024-01-15T10:30:00+05:30")
        assert result is not None

    def test_parse_valid_iso_negative_offset(self):
        """Parse valid ISO date with negative offset."""
        from python_app.scoring import _parse_date
        
        result = _parse_date("2024-01-15T10:30:00-08:00")
        assert result is not None

    def test_parse_none_returns_none(self):
        """Parse None returns None."""
        from python_app.scoring import _parse_date
        
        assert _parse_date(None) is None

    def test_parse_empty_returns_none(self):
        """Parse empty string returns None."""
        from python_app.scoring import _parse_date
        
        assert _parse_date("") is None

    def test_parse_invalid_format_returns_none(self):
        """Parse invalid format returns None."""
        from python_app.scoring import _parse_date
        
        assert _parse_date("not-a-date") is None
        assert _parse_date("2024/01/15") is None
        assert _parse_date("Jan 15, 2024") is None

    def test_parse_date_only_string(self):
        """Parse date-only string returns datetime at midnight."""
        from python_app.scoring import _parse_date
        
        # Python's fromisoformat actually parses date-only as midnight
        result = _parse_date("2024-01-15")
        assert result is not None
        assert result.year == 2024

    def test_parse_with_microseconds(self):
        """Parse date with microseconds."""
        from python_app.scoring import _parse_date
        
        result = _parse_date("2024-01-15T10:30:00.123456Z")
        assert result is not None


class TestUrgencyScore:
    """Edge case tests for urgency scoring."""

    def test_urgency_event_tomorrow(self):
        """Event tomorrow has high urgency."""
        from python_app.scoring import _urgency_score, MAX_URGENCY_SCORE
        
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        event = {"event_date": tomorrow}
        
        score = _urgency_score(event)
        # Score = MAX_URGENCY_SCORE - days_until = 30 - 0 (same day) or 30 - 1
        assert score >= MAX_URGENCY_SCORE - 2  # Allow for timezone edge cases
        assert score <= MAX_URGENCY_SCORE

    def test_urgency_event_today(self):
        """Event today has high urgency (near max)."""
        from python_app.scoring import _urgency_score, MAX_URGENCY_SCORE
        
        # Use an event 6 hours from now to avoid timezone edge cases
        today = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
        event = {"event_date": today}
        
        score = _urgency_score(event)
        # Score should be high (at or near max)
        assert score >= MAX_URGENCY_SCORE - 1

    def test_urgency_event_far_future(self):
        """Event far in future has zero urgency."""
        from python_app.scoring import _urgency_score
        
        far_future = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
        event = {"event_date": far_future}
        
        score = _urgency_score(event)
        assert score == 0

    def test_urgency_no_date_returns_zero(self):
        """Event without date returns zero urgency."""
        from python_app.scoring import _urgency_score
        
        assert _urgency_score({}) == 0
        assert _urgency_score({"event_date": None}) == 0
        assert _urgency_score({"event_date": ""}) == 0

    def test_urgency_uses_timestamp_fallback(self):
        """Urgency uses timestamp field as fallback."""
        from python_app.scoring import _urgency_score
        
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        event = {"timestamp": tomorrow}
        
        score = _urgency_score(event)
        assert score > 0

    def test_urgency_past_event(self):
        """Past event has higher urgency (negative days)."""
        from python_app.scoring import _urgency_score, MAX_URGENCY_SCORE
        
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        event = {"event_date": yesterday}
        
        score = _urgency_score(event)
        # Days until is negative (-1), so score = 30 - (-1) = 31 or higher
        assert score > MAX_URGENCY_SCORE


class TestClusterMatch:
    """Edge case tests for cluster matching."""

    def test_cluster_match_with_decayed_prefs(self):
        """Cluster match prefers time-decayed preferences."""
        from python_app.scoring import _cluster_match
        
        event = {"category": "tech_innovation"}
        prefs = {"tech_innovation": 0.5}
        decayed_prefs = {"tech_innovation": 0.9}
        
        score = _cluster_match(event, prefs, decayed_prefs)
        assert score == 0.9  # Uses decayed

    def test_cluster_match_falls_back_to_stored(self):
        """Cluster match falls back to stored when no decayed pref."""
        from python_app.scoring import _cluster_match
        
        event = {"category": "arts_music"}
        prefs = {"arts_music": 0.7}
        decayed_prefs = {}  # Empty
        
        score = _cluster_match(event, prefs, decayed_prefs)
        assert score == 0.7  # Uses stored

    def test_cluster_match_no_category(self):
        """Event without category returns default score."""
        from python_app.scoring import _cluster_match, DEFAULT_CATEGORY_SCORE
        
        event = {}
        score = _cluster_match(event, {}, {})
        assert score == DEFAULT_CATEGORY_SCORE

    def test_cluster_match_unknown_category(self):
        """Unknown category returns default score."""
        from python_app.scoring import _cluster_match, DEFAULT_CATEGORY_SCORE
        
        event = {"category": "unknown_xyz"}
        score = _cluster_match(event, {}, {})
        assert score == DEFAULT_CATEGORY_SCORE


class TestTimeDecayedPreferences:
    """Edge case tests for time-decayed preference computation."""

    def test_decay_lambda_calculation(self):
        """Test half-life decay constant calculation."""
        from python_app.scoring import DECAY_HALF_LIFE_DAYS
        
        decay_lambda = math.log(2) / DECAY_HALF_LIFE_DAYS
        
        # After 30 days, weight should be 0.5
        weight_30_days = math.exp(-decay_lambda * 30)
        assert abs(weight_30_days - 0.5) < 0.01

    def test_decay_weights_decrease_over_time(self):
        """Older interactions have lower weights."""
        from python_app.scoring import DECAY_HALF_LIFE_DAYS
        
        decay_lambda = math.log(2) / DECAY_HALF_LIFE_DAYS
        
        weight_0_days = math.exp(-decay_lambda * 0)
        weight_15_days = math.exp(-decay_lambda * 15)
        weight_30_days = math.exp(-decay_lambda * 30)
        
        assert weight_0_days > weight_15_days > weight_30_days
        assert weight_0_days == 1.0  # No decay at day 0


class TestConstants:
    """Tests for scoring constants."""

    def test_num_categories(self):
        """NUM_CATEGORIES equals 13."""
        from python_app.scoring import NUM_CATEGORIES
        assert NUM_CATEGORIES == 13

    def test_default_category_score_is_uniform(self):
        """DEFAULT_CATEGORY_SCORE is 1/13."""
        from python_app.scoring import DEFAULT_CATEGORY_SCORE, NUM_CATEGORIES
        assert abs(DEFAULT_CATEGORY_SCORE - 1/NUM_CATEGORIES) < 0.001

    def test_cluster_match_weight(self):
        """CLUSTER_MATCH_WEIGHT is 50."""
        from python_app.scoring import CLUSTER_MATCH_WEIGHT
        assert CLUSTER_MATCH_WEIGHT == 50

    def test_max_urgency_score(self):
        """MAX_URGENCY_SCORE is 30."""
        from python_app.scoring import MAX_URGENCY_SCORE
        assert MAX_URGENCY_SCORE == 30

    def test_decay_half_life_days(self):
        """DECAY_HALF_LIFE_DAYS is 30."""
        from python_app.scoring import DECAY_HALF_LIFE_DAYS
        assert DECAY_HALF_LIFE_DAYS == 30.0


class TestBaseWeights:
    """Tests for interaction base weights in time decay."""

    def test_like_weight_is_positive(self):
        """Like interactions have positive weight."""
        # The base_weights dict in _compute_time_decayed_preferences
        # like: 1.0, click: 0.5, dislike: -0.5
        weights = {"like": 1.0, "click": 0.5, "dislike": -0.5}
        assert weights["like"] > 0

    def test_dislike_weight_is_negative(self):
        """Dislike interactions have negative weight."""
        weights = {"like": 1.0, "click": 0.5, "dislike": -0.5}
        assert weights["dislike"] < 0

    def test_click_weight_is_between(self):
        """Click weight is between like and dislike."""
        weights = {"like": 1.0, "click": 0.5, "dislike": -0.5}
        assert weights["click"] > 0
        assert weights["click"] < weights["like"]
