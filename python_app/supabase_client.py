"""
Supabase client bootstrap.
"""

from supabase import create_client, Client

from .config import require_env, get_env

# Support both naming conventions used in the TS codebase
SUPABASE_URL = get_env("SUPABASE_URL") or get_env("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = get_env("SUPABASE_SERVICE_KEY") or get_env("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
  raise RuntimeError("Missing Supabase environment variables. Set SUPABASE_URL and SUPABASE_SERVICE_KEY (or SUPABASE_SECRET_KEY).")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
