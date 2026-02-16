"""OpenAI client bootstrap and retry logic for Connect3.

Provides a shared OpenAI client instance and a retry wrapper that handles
transient errors with exponential backoff while immediately re-raising
non-retryable errors (auth failures, bad requests).
"""

import time
from typing import Any, Callable, TypeVar

from openai import AuthenticationError, BadRequestError, OpenAI

from .config import get_env
from .logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Client singleton
# ---------------------------------------------------------------------------

_api_key = get_env("OPENAI_API_KEY")

client: OpenAI = OpenAI(api_key=_api_key) if _api_key else None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Retry configuration
# ---------------------------------------------------------------------------

OPENAI_MAX_RETRIES: int = 3
_RETRY_BASE_WAIT: float = 1.0  # seconds
_RETRY_MAX_WAIT: float = 10.0  # seconds

# Errors that should NOT be retried (deterministic failures)
_NON_RETRYABLE = (AuthenticationError, BadRequestError)


def with_retry(fn: Callable[..., T], *, label: str = "OpenAI call") -> T:
    """Execute *fn* with exponential-backoff retry on transient errors.

    Non-retryable errors (``AuthenticationError``, ``BadRequestError``) are
    re-raised immediately.  All other exceptions are retried up to
    ``OPENAI_MAX_RETRIES`` times.
    """
    last_exc: BaseException | None = None
    for attempt in range(1, OPENAI_MAX_RETRIES + 1):
        try:
            return fn()
        except _NON_RETRYABLE:
            raise  # deterministic – retrying won't help
        except Exception as exc:
            last_exc = exc
            if attempt < OPENAI_MAX_RETRIES:
                wait = min(_RETRY_BASE_WAIT * (2 ** (attempt - 1)), _RETRY_MAX_WAIT)
                logger.warning(
                    "%s attempt %d/%d failed (%s), retrying in %.1fs…",
                    label, attempt, OPENAI_MAX_RETRIES, exc, wait,
                )
                time.sleep(wait)
            else:
                logger.error(
                    "%s failed after %d attempts: %s", label, OPENAI_MAX_RETRIES, exc
                )
    raise last_exc  # type: ignore[misc]
