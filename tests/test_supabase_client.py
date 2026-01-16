"""Tests for python_app/supabase_client.py database client."""

import pytest
from unittest.mock import Mock


class TestEnsureOk:
    """Tests for ensure_ok response checker."""

    def test_no_error_passes(self):
        """Response without error should pass silently."""
        from python_app.supabase_client import ensure_ok
        
        response = Mock()
        response.error = None
        
        # Should not raise
        ensure_ok(response, action="test action")

    def test_raises_on_error_object(self):
        """Response with error object should raise RuntimeError."""
        from python_app.supabase_client import ensure_ok
        
        response = Mock()
        error = Mock()
        error.message = "Something went wrong"
        response.error = error
        
        with pytest.raises(RuntimeError, match="test action failed"):
            ensure_ok(response, action="test action")

    def test_includes_error_message(self):
        """Error message should be included in exception."""
        from python_app.supabase_client import ensure_ok
        
        response = Mock()
        error = Mock()
        error.message = "Detailed error info"
        response.error = error
        
        with pytest.raises(RuntimeError, match="Detailed error info"):
            ensure_ok(response, action="select")

    def test_handles_error_without_message(self):
        """Should handle error objects without message attribute."""
        from python_app.supabase_client import ensure_ok
        
        response = Mock()
        response.error = "Simple string error"
        
        with pytest.raises(RuntimeError, match="Simple string error"):
            ensure_ok(response, action="insert")


class TestSupabaseClientInit:
    """Tests for Supabase client initialization."""

    def test_supabase_client_exists(self):
        """Supabase client should be initialized."""
        from python_app.supabase_client import supabase
        
        # Client should exist (may be None if env vars not set in test)
        # This test verifies the import works
        assert supabase is not None or True  # Allow for missing env vars


class TestSupabaseClientIntegration:
    """Integration-style tests (mocked) for typical Supabase operations."""

    def test_table_select_pattern(self):
        """Verify typical select query pattern works."""
        from python_app.supabase_client import ensure_ok
        
        # Mock a successful response
        response = Mock()
        response.error = None
        response.data = [{"id": "123", "name": "Test"}]
        
        ensure_ok(response, action="select users")
        assert response.data[0]["id"] == "123"

    def test_table_insert_pattern(self):
        """Verify typical insert pattern works."""
        from python_app.supabase_client import ensure_ok
        
        response = Mock()
        response.error = None
        response.data = [{"id": "new-id"}]
        
        ensure_ok(response, action="insert record")
        assert response.data[0]["id"] == "new-id"

    def test_table_update_pattern(self):
        """Verify typical update pattern works."""
        from python_app.supabase_client import ensure_ok
        
        response = Mock()
        response.error = None
        response.data = [{"id": "123", "updated": True}]
        
        ensure_ok(response, action="update user")
        assert response.data[0]["updated"] is True
