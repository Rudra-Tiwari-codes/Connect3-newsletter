"""
Email delivery via Gmail SMTP (Python port of src/lib/email-delivery.ts).
"""

import os
import smtplib
from email.message import EmailMessage
from typing import Any, Dict, List

from .config import require_env, get_env
from .email_templates import generate_personalized_email
from .supabase_client import supabase


GMAIL_USER = require_env("GMAIL_USER")
GMAIL_APP_PASSWORD = require_env("GMAIL_APP_PASSWORD")
FROM_EMAIL = get_env("GMAIL_FROM_EMAIL") or GMAIL_USER
FEEDBACK_URL = get_env("NEXT_PUBLIC_APP_URL", "http://localhost:3000") + "/api/feedback"


def send_email(to_email: str, subject: str, html: str) -> None:
  msg = EmailMessage()
  msg["From"] = FROM_EMAIL
  msg["To"] = to_email
  msg["Subject"] = subject
  msg.set_content("HTML email requires an HTML-capable client.")
  msg.add_alternative(html, subtype="html")

  with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
    smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    smtp.send_message(msg)


def send_personalized_email(user: Dict[str, Any], events: List[Dict[str, Any]]) -> None:
  html = generate_personalized_email(user, events, FEEDBACK_URL)
  send_email(user["email"], f"Your Weekly Event Picks ({len(events)} events)", html)
  supabase.table("email_logs").insert({"user_id": user["id"], "status": "sent"}).execute()
