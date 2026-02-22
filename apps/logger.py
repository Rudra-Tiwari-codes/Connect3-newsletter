"""
Centralized logging configuration for Connect3.

Provides structured logging with consistent formatting across all modules.
Supports both console and file output with configurable log levels.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

LOG_LEVEL = "INFO"
LOG_FILE = None  # Optional file path for logging
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Map string levels to logging constants
LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def _get_level(level_str: str) -> int:
    """Convert string log level to logging constant."""
    return LEVEL_MAP.get(level_str.upper(), logging.INFO)


def setup_logging() -> None:
    """
    Configure root logger with handlers.
    
    Call this once at application startup (e.g., in main scripts).
    """
    root = logging.getLogger()
    root.setLevel(_get_level(LOG_LEVEL))
    
    # Clear existing handlers to avoid duplicates
    root.handlers.clear()
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(_get_level(LOG_LEVEL))
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    root.addHandler(console_handler)
    
    # File handler (optional)
    if LOG_FILE:
        log_path = Path(LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(_get_level(LOG_LEVEL))
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Usually __name__ of the calling module
        
    Returns:
        Configured logger instance
        
    Example:
        from python_app.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Processing started")
    """
    return logging.getLogger(name)


class LogContext:
    """
    Context manager for logging operation blocks with timing.
    
    Example:
        with LogContext(logger, "embedding generation"):
            # ... operations ...
        # Logs: "embedding generation completed in 1.23s"
    """
    
    def __init__(self, logger: logging.Logger, operation: str, level: int = logging.INFO):
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time: Optional[datetime] = None
    
    def __enter__(self) -> "LogContext":
        self.start_time = datetime.now()
        self.logger.log(self.level, f"{self.operation} started")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if exc_type:
            self.logger.error(f"{self.operation} failed after {elapsed:.2f}s: {exc_val}")
        else:
            self.logger.log(self.level, f"{self.operation} completed in {elapsed:.2f}s")
        return False  # Don't suppress exceptions
