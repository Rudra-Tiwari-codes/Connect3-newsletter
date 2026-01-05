"""Pytest configuration for Connect3 tests."""

import sys
from pathlib import Path

# Add project root to Python path so tests can import api and python_app
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
