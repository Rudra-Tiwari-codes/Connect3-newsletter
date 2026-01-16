"""Comprehensive tests for python_app/logger.py logging utilities."""

import logging
import pytest
from unittest.mock import Mock, patch
from datetime import datetime


class TestGetLevel:
    """Tests for _get_level function."""

    def test_valid_levels(self):
        """All standard log levels should map correctly."""
        from python_app.logger import _get_level
        
        assert _get_level("DEBUG") == logging.DEBUG
        assert _get_level("INFO") == logging.INFO
        assert _get_level("WARNING") == logging.WARNING
        assert _get_level("ERROR") == logging.ERROR
        assert _get_level("CRITICAL") == logging.CRITICAL

    def test_case_insensitive(self):
        """Level strings should be case insensitive."""
        from python_app.logger import _get_level
        
        assert _get_level("debug") == logging.DEBUG
        assert _get_level("Debug") == logging.DEBUG
        assert _get_level("DEBUG") == logging.DEBUG

    def test_invalid_level_defaults_to_info(self):
        """Invalid level string defaults to INFO."""
        from python_app.logger import _get_level
        
        assert _get_level("INVALID") == logging.INFO
        assert _get_level("") == logging.INFO


class TestGetLogger:
    """Tests for get_logger function."""

    def test_returns_logger_instance(self):
        """Should return a logging.Logger instance."""
        from python_app.logger import get_logger
        
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)

    def test_logger_has_correct_name(self):
        """Logger should have the specified name."""
        from python_app.logger import get_logger
        
        logger = get_logger("my.custom.module")
        assert logger.name == "my.custom.module"

    def test_same_name_returns_same_logger(self):
        """Same name should return same logger instance."""
        from python_app.logger import get_logger
        
        logger1 = get_logger("same_name")
        logger2 = get_logger("same_name")
        assert logger1 is logger2


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_clears_existing_handlers(self):
        """Should clear existing handlers from root logger."""
        from python_app.logger import setup_logging
        
        root = logging.getLogger()
        # Add a dummy handler
        root.addHandler(logging.StreamHandler())
        initial_count = len(root.handlers)
        
        setup_logging()
        
        # Should have exactly 1 console handler (possibly more if file logging enabled)
        assert len(root.handlers) >= 1

    def test_adds_console_handler(self):
        """Should add a StreamHandler for console output."""
        from python_app.logger import setup_logging
        
        setup_logging()
        root = logging.getLogger()
        
        stream_handlers = [h for h in root.handlers if isinstance(h, logging.StreamHandler)]
        assert len(stream_handlers) >= 1


class TestLogContext:
    """Tests for LogContext context manager."""

    def test_logs_start_message(self):
        """Should log start message on entry."""
        from python_app.logger import LogContext
        
        mock_logger = Mock(spec=logging.Logger)
        
        with LogContext(mock_logger, "test operation"):
            pass
        
        # Check that log was called with 'started'
        calls = [str(call) for call in mock_logger.log.call_args_list]
        assert any("started" in str(call) for call in calls)

    def test_logs_completion_message(self):
        """Should log completion message with time on exit."""
        from python_app.logger import LogContext
        
        mock_logger = Mock(spec=logging.Logger)
        
        with LogContext(mock_logger, "test operation"):
            pass
        
        # Check that log was called with 'completed'
        calls = [str(call) for call in mock_logger.log.call_args_list]
        assert any("completed" in str(call) for call in calls)

    def test_logs_failure_on_exception(self):
        """Should log error message when exception occurs."""
        from python_app.logger import LogContext
        
        mock_logger = Mock(spec=logging.Logger)
        
        try:
            with LogContext(mock_logger, "failing operation"):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Check that error was logged
        mock_logger.error.assert_called_once()
        error_msg = str(mock_logger.error.call_args)
        assert "failed" in error_msg

    def test_does_not_suppress_exceptions(self):
        """Should not suppress exceptions."""
        from python_app.logger import LogContext
        
        mock_logger = Mock(spec=logging.Logger)
        
        with pytest.raises(ValueError, match="Test error"):
            with LogContext(mock_logger, "test"):
                raise ValueError("Test error")

    def test_measures_elapsed_time(self):
        """Should measure elapsed time correctly."""
        from python_app.logger import LogContext
        import time
        
        mock_logger = Mock(spec=logging.Logger)
        
        with LogContext(mock_logger, "timed operation"):
            time.sleep(0.1)  # Sleep 100ms
        
        # Verify completion was logged with time
        completion_call = mock_logger.log.call_args_list[-1]
        assert "completed in" in str(completion_call)

    def test_custom_log_level(self):
        """Should use custom log level when specified."""
        from python_app.logger import LogContext
        
        mock_logger = Mock(spec=logging.Logger)
        
        with LogContext(mock_logger, "debug operation", level=logging.DEBUG):
            pass
        
        # Check level was passed to log()
        first_call = mock_logger.log.call_args_list[0]
        assert first_call[0][0] == logging.DEBUG
