"""Tests for api/unsubscribe.py token validation."""

import pytest
import hmac
import hashlib


def test_expected_token_generation():
    """Test that expected token is generated correctly."""
    from api.unsubscribe import _expected_token
    
    user_id = "test-user-123"
    secret = "test-secret-456"
    
    # Manually compute expected token
    manual_token = hmac.new(
        secret.encode("utf-8"),
        user_id.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    assert _expected_token(user_id, secret) == manual_token


def test_is_valid_token_valid():
    """Test that valid tokens pass validation."""
    from api.unsubscribe import _is_valid_token, _expected_token
    
    user_id = "user-abc"
    secret = "secret-xyz"
    valid_token = _expected_token(user_id, secret)
    
    assert _is_valid_token(user_id, valid_token, secret) is True


def test_is_valid_token_invalid():
    """Test that invalid tokens fail validation."""
    from api.unsubscribe import _is_valid_token
    
    assert _is_valid_token("user", "invalid-token", "secret") is False


def test_is_valid_token_empty():
    """Test that empty tokens fail validation."""
    from api.unsubscribe import _is_valid_token
    
    assert _is_valid_token("user", "", "secret") is False
    assert _is_valid_token("user", None, "secret") is False
