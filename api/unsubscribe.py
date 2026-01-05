"""
Vercel Serverless Function for email unsubscribe.
Marks a user as unsubscribed and returns a confirmation page or redirects.
"""

from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from datetime import datetime, timezone
import hashlib
import hmac
import logging
import os

logger = logging.getLogger(__name__)

from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
UNSUBSCRIBE_TOKEN_SECRET = os.environ.get("UNSUBSCRIBE_TOKEN_SECRET")
UNSUBSCRIBE_REDIRECT_URL = os.environ.get("UNSUBSCRIBE_REDIRECT_URL") or os.environ.get("UNSUBSCRIBE_CONFIRM_URL")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def _expected_token(user_id: str, secret: str) -> str:
    mac = hmac.new(secret.encode("utf-8"), user_id.encode("utf-8"), hashlib.sha256)
    return mac.hexdigest()


def _is_valid_token(user_id: str, token: str, secret: str) -> bool:
    if not token:
        return False
    return hmac.compare_digest(_expected_token(user_id, secret), token)


def _send_plain(handler: BaseHTTPRequestHandler, status: int, message: str) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", "text/plain; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(message.encode("utf-8"))


def _send_html(handler: BaseHTTPRequestHandler, status: int, html: str) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(html.encode("utf-8"))


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        user_id = params.get("uid", [None])[0]
        token = params.get("token", [None])[0]

        if not user_id:
            _send_plain(self, 400, "Missing uid.")
            return

        if not UNSUBSCRIBE_TOKEN_SECRET:
            _send_plain(self, 500, "Unsubscribe token secret not configured.")
            return
        if not _is_valid_token(user_id, token, UNSUBSCRIBE_TOKEN_SECRET):
            _send_plain(self, 403, "Invalid or missing token.")
            return

        if not supabase:
            _send_plain(self, 500, "Supabase not configured.")
            return

        try:
            payload = {
                "is_unsubscribed": True,
                "unsubscribed_at": datetime.now(timezone.utc).isoformat(),
            }
            supabase.table("users").update(payload).eq("id", user_id).execute()
        except Exception as exc:
            logger.error(f"Unsubscribe failed for user {user_id}: {exc}")
            _send_plain(self, 500, "An error occurred. Please try again later.")
            return

        if UNSUBSCRIBE_REDIRECT_URL:
            self.send_response(302)
            self.send_header("Location", UNSUBSCRIBE_REDIRECT_URL)
            self.end_headers()
            return

        html = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Unsubscribed</title>
  </head>
  <body style="margin:0; padding:24px; font-family:Arial, sans-serif; background:#f9fafb; color:#111827;">
    <div style="max-width:520px; margin:0 auto; background:#fff; padding:24px; border-radius:10px; border:1px solid #e5e7eb;">
      <h1 style="margin:0 0 12px 0; font-size:20px;">You're unsubscribed</h1>
      <p style="margin:0; color:#4b5563;">You will no longer receive Connect3 newsletters.</p>
    </div>
  </body>
</html>
        """
        _send_html(self, 200, html.strip())
