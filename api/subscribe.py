"""
Vercel Serverless Function for newsletter signups.
Stores a user in Supabase using server-side credentials.
"""

import json
import logging
import os
import re
from http.server import BaseHTTPRequestHandler

from supabase import create_client

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
USERS_TABLE = os.environ.get("SUPABASE_USERS_TABLE") or "users"
ALLOWED_ORIGIN = os.environ.get("SUBSCRIBE_ALLOWED_ORIGIN")

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


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

        record = {
            "name": f"{first_name} {last_name}".strip(),
            "email": email,
        }

        try:
            supabase.table(USERS_TABLE).insert(record).execute()
        except Exception as exc:
            logger.error("Signup failed: %s", exc)
            _send_json(self, 500, {"error": "Unable to save your details right now."})
            return

        _send_json(self, 200, {"ok": True})

