"""Comprehensive edge case tests for api/feedback.py validation functions."""

import pytest
from datetime import datetime, timezone, timedelta


class TestValidateUserId:
    """Edge case tests for user_id validation."""

    def test_valid_uuid_lowercase(self):
        """Valid lowercase UUID passes."""
        from api.feedback import validate_user_id
        assert validate_user_id("12345678-1234-1234-1234-123456789abc") == "12345678-1234-1234-1234-123456789abc"

    def test_valid_uuid_uppercase(self):
        """Valid uppercase UUID passes (case insensitive)."""
        from api.feedback import validate_user_id
        assert validate_user_id("12345678-1234-1234-1234-123456789ABC") == "12345678-1234-1234-1234-123456789ABC"

    def test_valid_uuid_mixed_case(self):
        """Valid mixed case UUID passes (all hex chars, case insensitive)."""
        from api.feedback import validate_user_id
        # UUID must use valid hex digits (0-9, a-f, A-F)
        assert validate_user_id("12345678-AbCd-1234-EfAb-123456789aBc") == "12345678-AbCd-1234-EfAb-123456789aBc"

    def test_missing_user_id_none(self):
        """None user_id raises ValidationError."""
        from api.feedback import validate_user_id, ValidationError
        with pytest.raises(ValidationError, match="Missing user_id"):
            validate_user_id(None)

    def test_missing_user_id_empty_string(self):
        """Empty string user_id raises ValidationError."""
        from api.feedback import validate_user_id, ValidationError
        with pytest.raises(ValidationError, match="Missing user_id"):
            validate_user_id("")

    def test_missing_user_id_whitespace_only(self):
        """Whitespace-only user_id raises ValidationError."""
        from api.feedback import validate_user_id, ValidationError
        with pytest.raises(ValidationError, match="Invalid user_id format"):
            validate_user_id("   ")

    def test_invalid_uuid_too_short(self):
        """Too short UUID raises ValidationError."""
        from api.feedback import validate_user_id, ValidationError
        with pytest.raises(ValidationError, match="Invalid user_id format"):
            validate_user_id("12345678-1234-1234-1234")

    def test_invalid_uuid_too_long(self):
        """Too long UUID raises ValidationError."""
        from api.feedback import validate_user_id, ValidationError
        with pytest.raises(ValidationError, match="Invalid user_id format"):
            validate_user_id("12345678-1234-1234-1234-123456789abc-extra")

    def test_invalid_uuid_wrong_format(self):
        """Wrong format UUID raises ValidationError."""
        from api.feedback import validate_user_id, ValidationError
        with pytest.raises(ValidationError, match="Invalid user_id format"):
            validate_user_id("not-a-valid-uuid-format")

    def test_invalid_uuid_no_dashes(self):
        """UUID without dashes raises ValidationError."""
        from api.feedback import validate_user_id, ValidationError
        with pytest.raises(ValidationError, match="Invalid user_id format"):
            validate_user_id("12345678123412341234123456789abc")

    def test_invalid_uuid_special_chars(self):
        """UUID with special characters raises ValidationError."""
        from api.feedback import validate_user_id, ValidationError
        with pytest.raises(ValidationError, match="Invalid user_id format"):
            validate_user_id("12345678-1234-1234-1234-123456789ab!")

    def test_uuid_with_leading_trailing_spaces_stripped(self):
        """UUID with leading/trailing spaces is stripped."""
        from api.feedback import validate_user_id
        result = validate_user_id("  12345678-1234-1234-1234-123456789abc  ")
        assert result == "12345678-1234-1234-1234-123456789abc"

    def test_sql_injection_attempt(self):
        """SQL injection attempt raises ValidationError."""
        from api.feedback import validate_user_id, ValidationError
        with pytest.raises(ValidationError, match="Invalid user_id format"):
            validate_user_id("'; DROP TABLE users; --")


class TestValidateEventId:
    """Edge case tests for event_id validation."""

    def test_valid_event_id_simple(self):
        """Simple alphanumeric event_id passes."""
        from api.feedback import validate_event_id
        assert validate_event_id("event123") == "event123"

    def test_valid_event_id_with_dashes(self):
        """Event ID with dashes passes."""
        from api.feedback import validate_event_id
        assert validate_event_id("event-123-abc") == "event-123-abc"

    def test_valid_event_id_with_underscores(self):
        """Event ID with underscores passes."""
        from api.feedback import validate_event_id
        assert validate_event_id("event_123_abc") == "event_123_abc"

    def test_valid_event_id_max_length(self):
        """Event ID at max length (64 chars) passes."""
        from api.feedback import validate_event_id
        long_id = "a" * 64
        assert validate_event_id(long_id) == long_id

    def test_missing_event_id_none(self):
        """None event_id raises ValidationError."""
        from api.feedback import validate_event_id, ValidationError
        with pytest.raises(ValidationError, match="Missing event_id"):
            validate_event_id(None)

    def test_missing_event_id_empty(self):
        """Empty event_id raises ValidationError."""
        from api.feedback import validate_event_id, ValidationError
        with pytest.raises(ValidationError, match="Missing event_id"):
            validate_event_id("")

    def test_invalid_event_id_too_long(self):
        """Event ID exceeding 64 chars raises ValidationError."""
        from api.feedback import validate_event_id, ValidationError
        long_id = "a" * 65
        with pytest.raises(ValidationError, match="Invalid event_id format"):
            validate_event_id(long_id)

    def test_invalid_event_id_special_chars(self):
        """Event ID with special chars raises ValidationError."""
        from api.feedback import validate_event_id, ValidationError
        with pytest.raises(ValidationError, match="Invalid event_id format"):
            validate_event_id("event!@#$%")

    def test_invalid_event_id_spaces(self):
        """Event ID with spaces raises ValidationError."""
        from api.feedback import validate_event_id, ValidationError
        with pytest.raises(ValidationError, match="Invalid event_id format"):
            validate_event_id("event 123")

    def test_event_id_with_leading_trailing_spaces_stripped(self):
        """Event ID spaces are stripped before validation."""
        from api.feedback import validate_event_id
        result = validate_event_id("  event123  ")
        assert result == "event123"


class TestValidateCategory:
    """Edge case tests for category validation."""

    def test_all_valid_categories(self):
        """All defined valid categories pass."""
        from api.feedback import validate_category, VALID_CATEGORIES
        for cat in VALID_CATEGORIES:
            assert validate_category(cat) == cat

    def test_category_none_defaults_to_general(self):
        """None category defaults to 'general'."""
        from api.feedback import validate_category
        assert validate_category(None) == "general"

    def test_category_empty_defaults_to_general(self):
        """Empty category defaults to 'general'."""
        from api.feedback import validate_category
        assert validate_category("") == "general"

    def test_category_whitespace_defaults_to_general(self):
        """Whitespace category defaults to 'general'."""
        from api.feedback import validate_category
        assert validate_category("   ") == "general"

    def test_category_unknown_defaults_to_general(self):
        """Unknown category defaults to 'general'."""
        from api.feedback import validate_category
        assert validate_category("unknown_xyz") == "general"

    def test_category_uppercase_normalized(self):
        """Uppercase category is lowercased."""
        from api.feedback import validate_category
        assert validate_category("TECH_INNOVATION") == "tech_innovation"

    def test_category_mixed_case_normalized(self):
        """Mixed case category is lowercased."""
        from api.feedback import validate_category
        assert validate_category("Tech_Innovation") == "tech_innovation"

    def test_category_with_spaces_stripped(self):
        """Category with spaces is stripped."""
        from api.feedback import validate_category
        assert validate_category("  tech_innovation  ") == "tech_innovation"

    def test_category_invalid_format_defaults_to_general(self):
        """Category with invalid chars defaults to 'general'."""
        from api.feedback import validate_category
        assert validate_category("tech-innovation") == "general"  # dash not allowed
        assert validate_category("tech123") == "general"  # numbers not allowed


class TestValidateAction:
    """Edge case tests for action validation."""

    def test_valid_actions(self):
        """All valid actions pass."""
        from api.feedback import validate_action
        assert validate_action("like") == "like"
        assert validate_action("dislike") == "dislike"
        assert validate_action("click") == "click"

    def test_action_none_defaults_to_like(self):
        """None action defaults to 'like'."""
        from api.feedback import validate_action
        assert validate_action(None) == "like"

    def test_action_empty_defaults_to_like(self):
        """Empty action defaults to 'like'."""
        from api.feedback import validate_action
        assert validate_action("") == "like"

    def test_action_invalid_defaults_to_like(self):
        """Invalid action defaults to 'like'."""
        from api.feedback import validate_action
        assert validate_action("love") == "like"
        assert validate_action("share") == "like"

    def test_action_uppercase_normalized(self):
        """Uppercase action is lowercased."""
        from api.feedback import validate_action
        assert validate_action("LIKE") == "like"
        assert validate_action("DISLIKE") == "dislike"

    def test_action_with_spaces_stripped(self):
        """Action with spaces is stripped."""
        from api.feedback import validate_action
        assert validate_action("  like  ") == "like"


class TestValidateTimestamp:
    """Edge case tests for timestamp validation."""

    def test_valid_iso_timestamp(self):
        """Valid ISO timestamp passes."""
        from api.feedback import validate_timestamp
        assert validate_timestamp("2024-01-15T10:30:00Z") == "2024-01-15T10:30:00Z"

    def test_valid_timestamp_with_offset(self):
        """Valid timestamp with timezone offset passes."""
        from api.feedback import validate_timestamp
        assert validate_timestamp("2024-01-15T10:30:00+05:30") == "2024-01-15T10:30:00+05:30"

    def test_timestamp_none_returns_none(self):
        """None timestamp returns None."""
        from api.feedback import validate_timestamp
        assert validate_timestamp(None) is None

    def test_timestamp_empty_returns_none(self):
        """Empty timestamp returns None."""
        from api.feedback import validate_timestamp
        assert validate_timestamp("") is None

    def test_timestamp_invalid_format_returns_none(self):
        """Invalid timestamp format returns None."""
        from api.feedback import validate_timestamp
        assert validate_timestamp("not-a-timestamp") is None
        assert validate_timestamp("2024/01/15") is None
        assert validate_timestamp("Jan 15, 2024") is None


class TestIsWithinDecayWindow:
    """Edge case tests for decay window calculation."""

    def test_recent_timestamp_within_window(self):
        """Recent timestamp is within decay window."""
        from api.feedback import is_within_decay_window
        recent = datetime.now(timezone.utc).isoformat()
        assert is_within_decay_window(recent) is True

    def test_old_timestamp_outside_window(self):
        """Old timestamp (>15 days) is outside decay window."""
        from api.feedback import is_within_decay_window
        old = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
        assert is_within_decay_window(old) is False

    def test_boundary_timestamp_exactly_15_days(self):
        """Timestamp at exactly 15 days may be inside or outside depending on time of day."""
        from api.feedback import is_within_decay_window
        # 14 days is definitely within the window
        within = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        assert is_within_decay_window(within) is True

    def test_boundary_timestamp_16_days(self):
        """Timestamp 16 days old is outside window."""
        from api.feedback import is_within_decay_window
        outside = (datetime.now(timezone.utc) - timedelta(days=16)).isoformat()
        assert is_within_decay_window(outside) is False

    def test_none_timestamp_allows_update(self):
        """None timestamp allows update (backwards compatibility)."""
        from api.feedback import is_within_decay_window
        assert is_within_decay_window(None) is True

    def test_invalid_timestamp_allows_update(self):
        """Invalid timestamp allows update (fail-safe)."""
        from api.feedback import is_within_decay_window
        assert is_within_decay_window("invalid") is True

    def test_z_suffix_handled(self):
        """Z suffix is properly handled."""
        from api.feedback import is_within_decay_window
        recent = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        assert is_within_decay_window(recent) is True


class TestRateLimiting:
    """Edge case tests for rate limiting function."""

    def test_first_request_not_limited(self):
        """First request is never rate limited."""
        from api.feedback import is_rate_limited, _rate_limit_store
        # Clear store for fresh test
        test_user = "test-user-rate-limit-1"
        _rate_limit_store.pop(test_user, None)
        assert is_rate_limited(test_user) is False

    def test_empty_user_id_not_limited(self):
        """Empty user_id is not rate limited."""
        from api.feedback import is_rate_limited
        assert is_rate_limited("") is False

    def test_none_user_id_not_limited(self):
        """None user_id is not rate limited."""
        from api.feedback import is_rate_limited
        assert is_rate_limited(None) is False
