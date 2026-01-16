"""Tests for python_app/openai_client.py retry logic."""

import pytest
from unittest.mock import Mock, patch
from openai import AuthenticationError, BadRequestError


class TestWithRetry:
    """Tests for the with_retry function."""

    def test_successful_call_returns_result(self):
        """Successful call returns result without retry."""
        from python_app.openai_client import with_retry
        
        mock_call = Mock(return_value="success")
        result = with_retry(mock_call, label="test")
        
        assert result == "success"
        assert mock_call.call_count == 1

    def test_retries_on_transient_error(self):
        """Retries on transient errors and succeeds."""
        from python_app.openai_client import with_retry
        
        # First call fails, second succeeds
        mock_call = Mock(side_effect=[ConnectionError("Network error"), "success"])
        result = with_retry(mock_call, label="test")
        
        assert result == "success"
        assert mock_call.call_count == 2

    def test_no_retry_on_auth_error(self):
        """Does not retry on AuthenticationError."""
        from python_app.openai_client import with_retry
        
        # Create a proper AuthenticationError
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.headers = {}
        auth_error = AuthenticationError(
            message="Invalid API key",
            response=mock_response,
            body=None
        )
        mock_call = Mock(side_effect=auth_error)
        
        with pytest.raises(AuthenticationError):
            with_retry(mock_call, label="test")
        
        assert mock_call.call_count == 1  # No retries

    def test_no_retry_on_bad_request(self):
        """Does not retry on BadRequestError."""
        from python_app.openai_client import with_retry
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.headers = {}
        bad_request = BadRequestError(
            message="Invalid request",
            response=mock_response,
            body=None
        )
        mock_call = Mock(side_effect=bad_request)
        
        with pytest.raises(BadRequestError):
            with_retry(mock_call, label="test")
        
        assert mock_call.call_count == 1  # No retries

    def test_exhausts_retries_on_persistent_error(self):
        """Raises after exhausting all retries."""
        from python_app.openai_client import with_retry, OPENAI_MAX_RETRIES
        
        mock_call = Mock(side_effect=ConnectionError("Network error"))
        
        with pytest.raises(ConnectionError):
            with_retry(mock_call, label="test")
        
        assert mock_call.call_count == OPENAI_MAX_RETRIES
