"""Comprehensive tests for python_app/email_templates.py."""

import pytest
from unittest.mock import patch


class TestFormatCategory:
    """Tests for format_category function."""

    def test_formats_underscore_separated(self):
        """Underscores become spaces, words capitalized."""
        from python_app.email_templates import format_category
        
        assert format_category("tech_innovation") == "Tech Innovation"
        assert format_category("career_networking") == "Career Networking"
        assert format_category("sports_fitness") == "Sports Fitness"

    def test_single_word(self):
        """Single word gets capitalized."""
        from python_app.email_templates import format_category
        
        assert format_category("general") == "General"

    def test_none_returns_general(self):
        """None category returns 'General'."""
        from python_app.email_templates import format_category
        
        assert format_category(None) == "General"

    def test_empty_returns_general(self):
        """Empty string returns 'General'."""
        from python_app.email_templates import format_category
        
        assert format_category("") == "General"


class TestTrackingBaseFromFeedbackUrl:
    """Tests for _tracking_base_from_feedback_url function."""

    def test_extracts_base_url(self):
        """Extracts scheme://netloc from full URL."""
        from python_app.email_templates import _tracking_base_from_feedback_url
        
        result = _tracking_base_from_feedback_url("https://example.com/feedback")
        assert result == "https://example.com"

    def test_handles_port(self):
        """Handles URLs with port numbers."""
        from python_app.email_templates import _tracking_base_from_feedback_url
        
        result = _tracking_base_from_feedback_url("http://localhost:3000/feedback")
        assert result == "http://localhost:3000"

    def test_fallback_on_invalid(self):
        """Falls back to default on invalid URL."""
        from python_app.email_templates import _tracking_base_from_feedback_url
        
        result = _tracking_base_from_feedback_url("not-a-url")
        assert "connect3" in result.lower()


class TestExpectedUnsubscribeToken:
    """Tests for _expected_unsubscribe_token function."""

    def test_generates_hex_token(self):
        """Should generate a hexadecimal token."""
        from python_app.email_templates import _expected_unsubscribe_token
        
        token = _expected_unsubscribe_token("user123", "secret")
        assert all(c in "0123456789abcdef" for c in token)

    def test_consistent_for_same_inputs(self):
        """Same user_id and secret should produce same token."""
        from python_app.email_templates import _expected_unsubscribe_token
        
        token1 = _expected_unsubscribe_token("user123", "secret")
        token2 = _expected_unsubscribe_token("user123", "secret")
        assert token1 == token2

    def test_different_for_different_users(self):
        """Different user_ids should produce different tokens."""
        from python_app.email_templates import _expected_unsubscribe_token
        
        token1 = _expected_unsubscribe_token("user1", "secret")
        token2 = _expected_unsubscribe_token("user2", "secret")
        assert token1 != token2

    def test_different_for_different_secrets(self):
        """Different secrets should produce different tokens."""
        from python_app.email_templates import _expected_unsubscribe_token
        
        token1 = _expected_unsubscribe_token("user123", "secret1")
        token2 = _expected_unsubscribe_token("user123", "secret2")
        assert token1 != token2


class TestGeneratePersonalizedEmail:
    """Tests for generate_personalized_email function."""

    def test_generates_html(self):
        """Should generate valid HTML structure."""
        from python_app.email_templates import generate_personalized_email
        
        user = {"id": "user-123", "name": "Test User", "email": "test@example.com"}
        events = [
            {"id": "evt1", "title": "Event 1", "description": "Desc 1", "category": "tech_innovation"}
        ]
        
        html = generate_personalized_email(user, events, "https://example.com/feedback")
        
        assert "<!DOCTYPE html>" in html
        assert "<html>" in html
        assert "</html>" in html

    def test_includes_user_name(self):
        """Should include user's name in greeting."""
        from python_app.email_templates import generate_personalized_email
        
        user = {"id": "user-123", "name": "Alice", "email": "alice@example.com"}
        events = []
        
        html = generate_personalized_email(user, events, "https://example.com/feedback")
        
        assert "Alice" in html

    def test_falls_back_to_email(self):
        """Should fall back to email if no name."""
        from python_app.email_templates import generate_personalized_email
        
        user = {"id": "user-123", "email": "bob@example.com"}
        events = []
        
        html = generate_personalized_email(user, events, "https://example.com/feedback")
        
        assert "bob@example.com" in html

    def test_includes_event_cards(self):
        """Should include cards for all events."""
        from python_app.email_templates import generate_personalized_email
        
        user = {"id": "user-123", "name": "User"}
        events = [
            {"id": "evt1", "title": "Event One", "description": "First event"},
            {"id": "evt2", "title": "Event Two", "description": "Second event"},
        ]
        
        html = generate_personalized_email(user, events, "https://example.com/feedback")
        
        assert "Event One" in html
        assert "Event Two" in html
        assert "First event" in html
        assert "Second event" in html
    
    def test_includes_event_media_image(self):
        """Should include event media image when available."""
        from python_app.email_templates import generate_personalized_email
        
        user = {"id": "user-123", "name": "User"}
        events = [{"id": "evt1", "title": "Test", "media_url": "https://example.com/image.jpg"}]
        
        html = generate_personalized_email(user, events, "https://example.com/feedback")
        
        assert 'src="https://example.com/image.jpg"' in html

    def test_includes_like_link_only(self):
        """Should include a like tracking link without any button labels."""
        from python_app.email_templates import generate_personalized_email
        
        user = {"id": "user-123", "name": "User"}
        events = [{"id": "evt1", "title": "Test", "category": "tech_innovation"}]
        
        html = generate_personalized_email(user, events, "https://example.com/feedback")
        
        assert "Interested" not in html
        assert "action=like" in html
        assert "Not interested" not in html
        assert "action=dislike" not in html

    def test_tracking_urls_include_event_info(self):
        """Tracking URLs should include event ID and category."""
        from python_app.email_templates import generate_personalized_email
        
        user = {"id": "user-123", "name": "User"}
        events = [{"id": "test-event-id", "title": "Test", "category": "sports_fitness"}]
        
        html = generate_personalized_email(user, events, "https://example.com/feedback")
        
        assert "eid=test-event-id" in html
        assert "cat=sports_fitness" in html
        assert "uid=user-123" in html

    @patch("python_app.email_templates.UNSUBSCRIBE_TOKEN_SECRET", "test-secret")
    def test_includes_unsubscribe_link_with_token(self):
        """Should include unsubscribe link with token when secret is set."""
        from python_app.email_templates import generate_personalized_email
        
        user = {"id": "user-123", "name": "User"}
        events = []
        
        html = generate_personalized_email(user, events, "https://example.com/feedback")
        
        assert "unsubscribe" in html.lower()
        assert "token=" in html

    def test_formats_category_nicely(self):
        """Category should be formatted with spaces and capitals."""
        from python_app.email_templates import generate_personalized_email
        
        user = {"id": "user-123", "name": "User"}
        events = [{"id": "evt1", "title": "Test", "category": "tech_innovation"}]
        
        html = generate_personalized_email(user, events, "https://example.com/feedback")
        
        assert "Tech Innovation" in html

    def test_handles_missing_event_fields(self):
        """Should handle events with missing optional fields."""
        from python_app.email_templates import generate_personalized_email
        
        user = {"id": "user-123", "name": "User"}
        events = [{"id": "evt1"}]  # Minimal event
        
        # Should not raise
        html = generate_personalized_email(user, events, "https://example.com/feedback")
        assert "Event" in html  # Default title

    def test_event_count_in_greeting(self):
        """Should show correct event count in greeting."""
        from python_app.email_templates import generate_personalized_email
        
        user = {"id": "user-123", "name": "User"}
        events = [{"id": f"evt{i}"} for i in range(5)]
        
        html = generate_personalized_email(user, events, "https://example.com/feedback")
        
        assert "5 events" in html
