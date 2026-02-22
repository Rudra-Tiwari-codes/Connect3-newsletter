"""Configuration helpers for the Python implementation."""

import os
from pathlib import Path
from typing import Optional

try:
  # Optional: load .env if python-dotenv is installed
  from dotenv import load_dotenv

  # Load .env in project root if present
  _root_dir = Path(__file__).resolve().parents[1]
  _root_env = _root_dir / ".env"
  if _root_env.exists():
    load_dotenv(_root_env)

  # Load .env.local after .env so local overrides take precedence
  _root_env_local = _root_dir / ".env.local"
  if _root_env_local.exists():
    load_dotenv(_root_env_local, override=True)
except Exception:
  # If python-dotenv isn't installed we silently continue; env vars must be set externally
  pass


def require_env(key: str) -> str:
  """Fetch an environment variable or raise a clear error."""
  value = os.getenv(key)
  if not value:
    raise RuntimeError(f"Missing environment variable: {key}")
  return value


def get_env(key: str, default: Optional[str] = None) -> Optional[str]:
  """Fetch an environment variable with an optional default."""
  return os.getenv(key, default)
