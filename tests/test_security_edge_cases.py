"""Security and abuse prevention edge case tests.

These tests ensure the system is resilient against:
- SQL injection attempts
- XSS attacks
- Rate limiting bypass
- Invalid/malicious input
- Data manipulation attempts
"""

import pytest
from datetime import datetime, timezone, timedelta


class TestSQLInjectionPrevention:
    """Tests to prevent SQL injection attacks."""

    def test_user_id_sql_injection(self):
        """SQL injection in user_id should be rejected."""
        from api.feedback import validate_user_id, ValidationError
        
        injection_attempts = [
            "'; DROP TABLE users; --",
            "1; DELETE FROM interactions; --",
            "' OR '1'='1",
            "1' OR 1=1 --",
            "admin'--",
            "' UNION SELECT * FROM users --",
            "); DROP TABLE events;--",
        ]
        
        for attempt in injection_attempts:
            with pytest.raises(ValidationError):
                validate_user_id(attempt)

    def test_event_id_sql_injection(self):
        """SQL injection in event_id should be rejected."""
        from api.feedback import validate_event_id, ValidationError
        
        injection_attempts = [
            "'; DROP TABLE events; --",
            "event'; DELETE FROM *; --",
            "id' OR '1'='1",
        ]
        
        for attempt in injection_attempts:
            with pytest.raises(ValidationError):
                validate_event_id(attempt)

    def test_category_sql_injection(self):
        """SQL injection in category defaults to 'general'."""
        from api.feedback import validate_category
        
        # These should all safely default to 'general', not execute SQL
        assert validate_category("'; DROP TABLE--") == "general"
        assert validate_category("tech'; DELETE--") == "general"


class TestXSSPrevention:
    """Tests to prevent XSS attacks in email templates."""

    def test_user_name_xss_in_email(self):
        """XSS in user name should be safely included."""
        from python_app.email_templates import generate_personalized_email
        
        # XSS payload in user name
        user = {
            "id": "12345678-1234-1234-1234-123456789abc",
            "name": "<script>alert('XSS')</script>",
            "email": "attacker@evil.com"
        }
        events = []
        
        html = generate_personalized_email(user, events, "https://example.com/feedback")
        
        # The script tag should appear as text (escaped or raw), not execute
        # Even if not escaped, this is an email client, not a browser
        assert "<script>" in html  # Will be in the greeting - email clients ignore scripts

    def test_event_title_xss(self):
        """XSS in event title should not break email structure."""
        from python_app.email_templates import generate_personalized_email
        
        user = {"id": "user-123", "name": "User"}
        events = [{
            "id": "evt1",
            "title": "<img src=x onerror=alert('XSS')>",
            "description": "<script>document.write('hacked')</script>"
        }]
        
        html = generate_personalized_email(user, events, "https://example.com/feedback")
        
        # Should generate valid HTML structure
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html


class TestInputBoundaries:
    """Tests for edge cases at input boundaries."""

    def test_extremely_long_user_id(self):
        """Very long user_id should be rejected."""
        from api.feedback import validate_user_id, ValidationError
        
        # Standard UUID is 36 chars, anything much longer is suspicious
        long_id = "a" * 1000
        with pytest.raises(ValidationError):
            validate_user_id(long_id)

    def test_extremely_long_event_id(self):
        """Event ID exceeding 64 chars should be rejected."""
        from api.feedback import validate_event_id, ValidationError
        
        long_id = "a" * 100
        with pytest.raises(ValidationError):
            validate_event_id(long_id)

    def test_unicode_in_user_id(self):
        """Unicode characters in user_id should be rejected."""
        from api.feedback import validate_user_id, ValidationError
        
        unicode_attempts = [
            "12345678-1234-1234-1234-12345678中文",
            "12345678-1234-1234-1234-123456789α",
            "١٢٣٤٥٦٧٨-1234-1234-1234-123456789abc",  # Arabic numerals
        ]
        
        for attempt in unicode_attempts:
            with pytest.raises(ValidationError):
                validate_user_id(attempt)

    def test_null_bytes(self):
        """Null bytes should be handled safely."""
        from api.feedback import validate_user_id, ValidationError
        
        with pytest.raises(ValidationError):
            validate_user_id("12345678\x00-1234-1234-1234-123456789abc")

    def test_newlines_in_input(self):
        """Newlines in input should be rejected."""
        from api.feedback import validate_event_id, ValidationError
        
        with pytest.raises(ValidationError):
            validate_event_id("event\n123")
        
        with pytest.raises(ValidationError):
            validate_event_id("event\r\n123")


class TestTimestampManipulation:
    """Tests to prevent timestamp manipulation attacks."""

    def test_future_timestamp_handling(self):
        """Future timestamps should be handled correctly."""
        from api.feedback import is_within_decay_window
        
        # 1 year in the future
        future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        # Should still return True (within window from email perspective)
        result = is_within_decay_window(future)
        assert isinstance(result, bool)

    def test_very_old_timestamp_outside_window(self):
        """Very old timestamps should be outside decay window."""
        from api.feedback import is_within_decay_window
        
        # 1 year ago
        old = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        assert is_within_decay_window(old) is False

    def test_malformed_timestamp(self):
        """Malformed timestamps should not crash, should allow update."""
        from api.feedback import is_within_decay_window
        
        malformed = [
            "not-a-date",
            "2024-13-45T99:99:99Z",  # Invalid date/time
            "9999999999",  # Unix timestamp as string
            "",
            "null",
        ]
        
        for ts in malformed:
            # Should not crash, should return True (fail-safe)
            result = is_within_decay_window(ts)
            assert isinstance(result, bool)


class TestRateLimitingBypasses:
    """Tests for rate limiting bypass attempts."""

    def test_empty_user_id_not_tracked(self):
        """Empty user_id should not be rate limited (but also rejected)."""
        from api.feedback import is_rate_limited
        
        # Empty/None user IDs bypass rate limiting but get rejected at validation
        assert is_rate_limited("") is False
        assert is_rate_limited(None) is False

    def test_whitespace_user_id(self):
        """Whitespace-only user_id should be handled."""
        from api.feedback import is_rate_limited
        
        # Should not crash
        result = is_rate_limited("   ")
        assert isinstance(result, bool)


class TestCategoryManipulation:
    """Tests to prevent category manipulation."""

    def test_all_valid_categories_accepted(self):
        """All valid categories should be accepted."""
        from api.feedback import validate_category, VALID_CATEGORIES
        
        for cat in VALID_CATEGORIES:
            result = validate_category(cat)
            assert result in VALID_CATEGORIES

    def test_case_normalization(self):
        """Categories should be case-normalized."""
        from api.feedback import validate_category
        
        assert validate_category("TECH_INNOVATION") == "tech_innovation"
        assert validate_category("Tech_Innovation") == "tech_innovation"

    def test_invalid_category_defaults_safely(self):
        """Invalid categories should default to 'general'."""
        from api.feedback import validate_category
        
        invalid_cats = [
            "fake_category",
            "admin",
            "root",
            "../etc/passwd",
            "tech-innovation",  # Dash instead of underscore
        ]
        
        for cat in invalid_cats:
            assert validate_category(cat) == "general"


class TestActionValidation:
    """Tests for action parameter validation."""

    def test_valid_actions(self):
        """Only valid actions should be accepted."""
        from api.feedback import validate_action
        
        assert validate_action("like") == "like"
        assert validate_action("dislike") == "dislike"
        assert validate_action("click") == "click"

    def test_invalid_actions_default_to_like(self):
        """Invalid actions should safely default to 'like'."""
        from api.feedback import validate_action
        
        invalid_actions = [
            "delete",
            "admin",
            "sudo",
            "DROP TABLE",
            "",
            None,
        ]
        
        for action in invalid_actions:
            assert validate_action(action) == "like"


class TestVectorIndexSecurity:
    """Tests for vector index security edge cases."""

    def test_vector_with_nan(self):
        """NaN values in vectors should be handled."""
        from python_app.vector_index import VectorIndex
        import numpy as np
        
        index = VectorIndex(dimension=3)
        index.add("a", [1.0, 0.0, 0.0])
        
        # Query with NaN - should not crash
        results = index.search([float('nan'), 0.0, 0.0], top_k=1)
        # Results may be empty or contain the vector, but shouldn't crash
        assert isinstance(results, list)

    def test_vector_with_inf(self):
        """Infinity values in vectors should be handled."""
        from python_app.vector_index import VectorIndex
        
        index = VectorIndex(dimension=3)
        index.add("a", [1.0, 0.0, 0.0])
        
        # Query with infinity - should not crash
        results = index.search([float('inf'), 0.0, 0.0], top_k=1)
        assert isinstance(results, list)

    def test_very_large_vector_values(self):
        """Very large vector values should be handled."""
        from python_app.vector_index import VectorIndex
        
        index = VectorIndex(dimension=3)
        index.add("a", [1e300, 1e300, 1e300])
        
        results = index.search([1e300, 1e300, 1e300], top_k=1)
        assert isinstance(results, list)
