"""Tests for api/feedback.py validation functions."""

import pytest


def test_validate_user_id_valid():
    """Test that valid UUIDs pass validation."""
    from api.feedback import validate_user_id
    
    valid_uuid = "12345678-1234-1234-1234-123456789abc"
    assert validate_user_id(valid_uuid) == valid_uuid


def test_validate_user_id_missing():
    """Test that missing user_id raises ValidationError."""
    from api.feedback import validate_user_id, ValidationError
    
    with pytest.raises(ValidationError, match="Missing user_id"):
        validate_user_id(None)


def test_validate_user_id_invalid_format():
    """Test that invalid UUIDs raise ValidationError."""
    from api.feedback import validate_user_id, ValidationError
    
    with pytest.raises(ValidationError, match="Invalid user_id format"):
        validate_user_id("not-a-valid-uuid")


def test_validate_event_id_valid():
    """Test that valid event IDs pass validation."""
    from api.feedback import validate_event_id
    
    valid_id = "event-123_abc"
    assert validate_event_id(valid_id) == valid_id


def test_validate_event_id_missing():
    """Test that missing event_id raises ValidationError."""
    from api.feedback import validate_event_id, ValidationError
    
    with pytest.raises(ValidationError, match="Missing event_id"):
        validate_event_id(None)


def test_validate_category_valid():
    """Test that valid categories pass validation."""
    from api.feedback import validate_category
    
    assert validate_category("tech_innovation") == "tech_innovation"


def test_validate_category_unknown_defaults_to_general():
    """Test that unknown categories default to 'general'."""
    from api.feedback import validate_category
    
    assert validate_category("unknown_category") == "general"


def test_validate_action_valid():
    """Test that valid actions pass validation."""
    from api.feedback import validate_action
    
    assert validate_action("like") == "like"
    assert validate_action("dislike") == "dislike"
    assert validate_action("click") == "click"


def test_validate_action_invalid_defaults_to_like():
    """Test that invalid actions default to 'like'."""
    from api.feedback import validate_action
    
    assert validate_action("invalid") == "like"


def test_is_within_decay_window_recent():
    """Test that recent emails are within decay window."""
    from api.feedback import is_within_decay_window
    from datetime import datetime, timezone
    
    recent = datetime.now(timezone.utc).isoformat()
    assert is_within_decay_window(recent) is True


def test_is_within_decay_window_none():
    """Test that None timestamp allows update (backwards compatibility)."""
    from api.feedback import is_within_decay_window
    
    assert is_within_decay_window(None) is True
