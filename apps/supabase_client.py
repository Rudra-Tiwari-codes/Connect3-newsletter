"""
Supabase client bootstrap.
"""

from supabase import create_client, Client

from .config import require_env, get_env

# Use the env names defined in the project .env
SUPABASE_URL = get_env("SUPABASE_URL")
SUPABASE_KEY = (
  get_env("SUPABASE_SERVICE_KEY")
  or get_env("SUPABASE_SECRET_KEY")
  or get_env("SUPABASE_KEY")
)

if not SUPABASE_URL or not SUPABASE_KEY:
  raise RuntimeError("Missing Supabase environment variables. Set SUPABASE_URL and SUPABASE_SERVICE_KEY (or SUPABASE_SECRET_KEY).")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def ensure_ok(response, *, action: str) -> None:
  """Raise a clear error when a Supabase response includes an error."""
  error = getattr(response, "error", None)
  if not error:
    return
  message = getattr(error, "message", None) or str(error)
  raise RuntimeError(f"Supabase {action} failed: {message}")
