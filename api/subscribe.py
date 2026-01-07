"""
Vercel Serverless Function for newsletter signups.
Stores a user in Supabase using server-side credentials.
"""

import json
import logging
import os
import re
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

# Add parent directory to path for python_app imports in Vercel serverless
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python_app.supabase_client import supabase

logger = logging.getLogger(__name__)

USERS_TABLE = os.environ.get("SUPABASE_USERS_TABLE") or "users"
ALLOWED_ORIGIN = os.environ.get("SUBSCRIBE_ALLOWED_ORIGIN")

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _get_allowed_origin(handler: BaseHTTPRequestHandler) -> str:
    if ALLOWED_ORIGIN:
        return ALLOWED_ORIGIN
    request_origin = handler.headers.get("Origin")
    return request_origin or "*"


def _send_json(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    handler.send_response(status)
    handler.send_header("Access-Control-Allow-Origin", _get_allowed_origin(handler))
    handler.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Vary", "Origin")
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(json.dumps(payload).encode("utf-8"))


def _read_json(handler: BaseHTTPRequestHandler) -> dict | None:
    content_length = int(handler.headers.get("Content-Length", "0"))
    if content_length <= 0:
        return None
    raw = handler.rfile.read(content_length)
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return None


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", _get_allowed_origin(self))
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Vary", "Origin")
        self.end_headers()

    def do_POST(self):
        if not supabase:
            _send_json(self, 500, {"error": "Supabase not configured."})
            return

        payload = _read_json(self)
        if not isinstance(payload, dict):
            _send_json(self, 400, {"error": "Invalid JSON body."})
            return

        first_name = str(payload.get("firstName") or "").strip()
        last_name = str(payload.get("lastName") or "").strip()
        email = str(payload.get("email") or "").strip()

        if not first_name or not last_name or not email:
            _send_json(
                self,
                400,
                {"error": "First name, last name, and email are required."},
            )
            return

        if not EMAIL_PATTERN.match(email):
            _send_json(self, 400, {"error": "Please provide a valid email address."})
            return

        # Check for existing user with this email
        try:
            existing = (
                supabase.table(USERS_TABLE)
                .select("id, is_unsubscribed")
                .eq("email", email)
                .limit(1)
                .execute()
            )
            if existing.data:
                # User exists - check if they unsubscribed and want to resubscribe
                if existing.data[0].get("is_unsubscribed"):
                    # Reactivate the unsubscribed user
                    supabase.table(USERS_TABLE).update({
                        "is_unsubscribed": False,
                        "unsubscribed_at": None,
                        "name": f"{first_name} {last_name}".strip(),
                    }).eq("id", existing.data[0]["id"]).execute()
                    _send_json(self, 200, {"ok": True, "resubscribed": True})
                    return
                else:
                    _send_json(self, 409, {"error": "This email is already subscribed."})
                    return
        except Exception as exc:
            logger.error("Failed to check existing user: %s", exc)
            _send_json(self, 500, {"error": "Unable to process your request right now."})
            return

        record = {
            "name": f"{first_name} {last_name}".strip(),
            "email": email,
            "is_new_recipient": True,
            "is_unsubscribed": False,
        }

        try:
            resp = supabase.table(USERS_TABLE).insert(record).execute()
            # Check if response has data (successful insert)
            if not resp.data:
                # Log the full response for debugging
                logger.error("Insert returned no data. Response: %s", resp)
                _send_json(self, 500, {"error": "Unable to save your details right now."})
                return
            logger.info("Successfully inserted user: %s", email)
        except Exception as exc:
            logger.error("Signup failed with exception: %s", exc)
            _send_json(self, 500, {"error": f"Unable to save your details: {str(exc)}"})
            return

        _send_json(self, 200, {"ok": True})

