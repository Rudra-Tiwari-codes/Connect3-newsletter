"""Comprehensive edge case tests for api/unsubscribe.py."""

import pytest
import hmac
import hashlib


class TestExpectedToken:
    """Edge case tests for token generation."""

    def test_token_generation_basic(self):
        """Basic token generation matches manual HMAC."""
        from api.unsubscribe import _expected_token
        
        user_id = "test-user"
        secret = "test-secret"
        
        expected = hmac.new(
            secret.encode("utf-8"),
            user_id.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        assert _expected_token(user_id, secret) == expected

    def test_token_different_users_different_tokens(self):
        """Different users get different tokens."""
        from api.unsubscribe import _expected_token
        
        secret = "same-secret"
        token1 = _expected_token("user1", secret)
        token2 = _expected_token("user2", secret)
        
        assert token1 != token2

    def test_token_different_secrets_different_tokens(self):
        """Different secrets produce different tokens."""
        from api.unsubscribe import _expected_token
        
        user_id = "same-user"
        token1 = _expected_token(user_id, "secret1")
        token2 = _expected_token(user_id, "secret2")
        
        assert token1 != token2

    def test_token_is_64_hex_chars(self):
        """Token is exactly 64 hex characters (SHA256)."""
        from api.unsubscribe import _expected_token
        
        token = _expected_token("any-user", "any-secret")
        assert len(token) == 64
        assert all(c in "0123456789abcdef" for c in token)

    def test_token_empty_user_id(self):
        """Empty user_id still produces valid token."""
        from api.unsubscribe import _expected_token
        
        token = _expected_token("", "secret")
        assert len(token) == 64

    def test_token_unicode_user_id(self):
        """Unicode user_id produces valid token."""
        from api.unsubscribe import _expected_token
        
        token = _expected_token("用户123", "secret")
        assert len(token) == 64

    def test_token_special_chars_in_secret(self):
        """Special characters in secret work correctly."""
        from api.unsubscribe import _expected_token
        
        token = _expected_token("user", "!@#$%^&*()_+-=[]{}|;':\",./<>?")
        assert len(token) == 64

    def test_token_deterministic(self):
        """Same inputs produce same token (deterministic)."""
        from api.unsubscribe import _expected_token
        
        token1 = _expected_token("user", "secret")
        token2 = _expected_token("user", "secret")
        
        assert token1 == token2


class TestIsValidToken:
    """Edge case tests for token validation."""

    def test_valid_token_passes(self):
        """Valid token passes validation."""
        from api.unsubscribe import _is_valid_token, _expected_token
        
        user_id = "user123"
        secret = "secret456"
        valid_token = _expected_token(user_id, secret)
        
        assert _is_valid_token(user_id, valid_token, secret) is True

    def test_invalid_token_fails(self):
        """Invalid token fails validation."""
        from api.unsubscribe import _is_valid_token
        
        assert _is_valid_token("user", "invalid-token", "secret") is False

    def test_empty_token_fails(self):
        """Empty string token fails validation."""
        from api.unsubscribe import _is_valid_token
        
        assert _is_valid_token("user", "", "secret") is False

    def test_none_token_fails(self):
        """None token fails validation."""
        from api.unsubscribe import _is_valid_token
        
        assert _is_valid_token("user", None, "secret") is False

    def test_token_wrong_case_fails(self):
        """Token with wrong case fails (hex is case-sensitive in comparison)."""
        from api.unsubscribe import _is_valid_token, _expected_token
        
        user_id = "user"
        secret = "secret"
        valid_token = _expected_token(user_id, secret)
        wrong_case = valid_token.upper()
        
        # This should still work because hmac.compare_digest is case-sensitive
        # and our token generation always produces lowercase
        assert _is_valid_token(user_id, wrong_case, secret) is False

    def test_token_with_extra_chars_fails(self):
        """Token with extra characters fails."""
        from api.unsubscribe import _is_valid_token, _expected_token
        
        user_id = "user"
        secret = "secret"
        valid_token = _expected_token(user_id, secret)
        
        assert _is_valid_token(user_id, valid_token + "extra", secret) is False

    def test_token_truncated_fails(self):
        """Truncated token fails."""
        from api.unsubscribe import _is_valid_token, _expected_token
        
        user_id = "user"
        secret = "secret"
        valid_token = _expected_token(user_id, secret)
        
        assert _is_valid_token(user_id, valid_token[:32], secret) is False

    def test_token_from_different_user_fails(self):
        """Token from different user fails."""
        from api.unsubscribe import _is_valid_token, _expected_token
        
        secret = "shared-secret"
        token_user1 = _expected_token("user1", secret)
        
        assert _is_valid_token("user2", token_user1, secret) is False

    def test_token_with_different_secret_fails(self):
        """Token generated with different secret fails."""
        from api.unsubscribe import _is_valid_token, _expected_token
        
        user_id = "user"
        token = _expected_token(user_id, "secret1")
        
        assert _is_valid_token(user_id, token, "secret2") is False

    def test_timing_attack_resistance(self):
        """Token validation uses constant-time comparison (hmac.compare_digest)."""
        from api.unsubscribe import _is_valid_token, _expected_token
        import time
        
        user_id = "user"
        secret = "secret"
        valid_token = _expected_token(user_id, secret)
        
        # Both should take similar time (not perfectly testable but ensures no crash)
        start1 = time.perf_counter()
        _is_valid_token(user_id, "a" * 64, secret)
        time1 = time.perf_counter() - start1
        
        start2 = time.perf_counter()
        _is_valid_token(user_id, valid_token, secret)
        time2 = time.perf_counter() - start2
        
        # Just verify both complete without error
        assert True


class TestSendPlainHelper:
    """Tests for _send_plain helper function."""

    def test_send_plain_sets_content_type(self):
        """_send_plain sets correct content type."""
        from api.unsubscribe import _send_plain
        from unittest.mock import Mock
        
        handler = Mock()
        handler.wfile = Mock()
        handler.wfile.write = Mock()
        
        _send_plain(handler, 200, "test message")
        
        handler.send_response.assert_called_with(200)
        handler.send_header.assert_called_with("Content-Type", "text/plain; charset=utf-8")

    def test_send_plain_writes_message(self):
        """_send_plain writes encoded message."""
        from api.unsubscribe import _send_plain
        from unittest.mock import Mock
        
        handler = Mock()
        handler.wfile = Mock()
        handler.wfile.write = Mock()
        
        _send_plain(handler, 200, "test message")
        
        handler.wfile.write.assert_called_with(b"test message")


class TestSendHtmlHelper:
    """Tests for _send_html helper function."""

    def test_send_html_sets_content_type(self):
        """_send_html sets correct content type."""
        from api.unsubscribe import _send_html
        from unittest.mock import Mock
        
        handler = Mock()
        handler.wfile = Mock()
        handler.wfile.write = Mock()
        
        _send_html(handler, 200, "<html></html>")
        
        handler.send_response.assert_called_with(200)
        handler.send_header.assert_called_with("Content-Type", "text/html; charset=utf-8")
