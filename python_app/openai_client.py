"""Shared OpenAI client configuration with basic retry support."""

from __future__ import annotations

import random
import time
from typing import Callable, TypeVar

from openai import OpenAI

from .config import get_env, require_env

OPENAI_API_KEY = require_env("OPENAI_API_KEY")
OPENAI_TIMEOUT_SEC = max(1, int(get_env("OPENAI_TIMEOUT_SEC", "30") or "30"))
OPENAI_MAX_RETRIES = max(1, int(get_env("OPENAI_MAX_RETRIES", "3") or "3"))

client = OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_TIMEOUT_SEC)

T = TypeVar("T")


def with_retry(call: Callable[[], T], *, label: str) -> T:
  for attempt in range(1, OPENAI_MAX_RETRIES + 1):
    try:
      return call()
    except Exception as exc:
      if attempt >= OPENAI_MAX_RETRIES:
        raise
      sleep_for = 0.5 * attempt + random.random() * 0.2
      print(f"{label} failed (attempt {attempt}): {exc}. Retrying in {sleep_for:.1f}s")
      time.sleep(sleep_for)
  raise RuntimeError(f"{label} failed after {OPENAI_MAX_RETRIES} attempts")
