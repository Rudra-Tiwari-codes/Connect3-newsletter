"""Tests for python_app/config.py configuration helpers."""

import os
import pytest


class TestRequireEnv:
    """Tests for require_env function."""

    def test_require_env_returns_value_when_set(self, monkeypatch):
        """Returns value when environment variable is set."""
        from python_app.config import require_env
        
        monkeypatch.setenv("TEST_VAR", "test_value")
        assert require_env("TEST_VAR") == "test_value"

    def test_require_env_raises_when_missing(self, monkeypatch):
        """Raises RuntimeError when environment variable is missing."""
        from python_app.config import require_env
        
        monkeypatch.delenv("MISSING_VAR", raising=False)
        with pytest.raises(RuntimeError, match="Missing environment variable: MISSING_VAR"):
            require_env("MISSING_VAR")

    def test_require_env_raises_when_empty(self, monkeypatch):
        """Raises RuntimeError when environment variable is empty string."""
        from python_app.config import require_env
        
        monkeypatch.setenv("EMPTY_VAR", "")
        with pytest.raises(RuntimeError, match="Missing environment variable: EMPTY_VAR"):
            require_env("EMPTY_VAR")


class TestGetEnv:
    """Tests for get_env function."""

    def test_get_env_returns_value_when_set(self, monkeypatch):
        """Returns value when environment variable is set."""
        from python_app.config import get_env
        
        monkeypatch.setenv("TEST_VAR", "test_value")
        assert get_env("TEST_VAR") == "test_value"

    def test_get_env_returns_default_when_missing(self, monkeypatch):
        """Returns default when environment variable is missing."""
        from python_app.config import get_env
        
        monkeypatch.delenv("MISSING_VAR", raising=False)
        assert get_env("MISSING_VAR", "default") == "default"

    def test_get_env_returns_none_when_missing_no_default(self, monkeypatch):
        """Returns None when missing and no default provided."""
        from python_app.config import get_env
        
        monkeypatch.delenv("MISSING_VAR", raising=False)
        assert get_env("MISSING_VAR") is None

    def test_get_env_returns_empty_string_when_empty(self, monkeypatch):
        """Returns empty string when variable is set to empty."""
        from python_app.config import get_env
        
        monkeypatch.setenv("EMPTY_VAR", "")
        assert get_env("EMPTY_VAR") == ""
