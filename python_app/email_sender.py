"""Email delivery via Gmail SMTP for Connect3 newsletters."""

import smtplib
import time
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any, Dict, List, Mapping

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .config import get_env
from .email_templates import generate_personalized_email
from .logger import get_logger
from .supabase_client import ensure_ok, supabase

logger = get_logger(__name__)


GMAIL_USER = get_env("GMAIL_USER")
GMAIL_APP_PASSWORD = get_env("GMAIL_APP_PASSWORD")
FROM_EMAIL = get_env("GMAIL_FROM_EMAIL") or GMAIL_USER or "noreply@example.com"
FEEDBACK_URL = "https://connect3-newsletter.vercel.app/feedback"
SMTP_TIMEOUT_SEC = max(1, int(get_env("SMTP_TIMEOUT_SEC", "30") or "30"))


@retry(
  stop=stop_after_attempt(3),
  wait=wait_exponential(multiplier=1, min=2, max=10),
  retry=retry_if_exception_type((smtplib.SMTPException, OSError)),
  reraise=True
)
def send_email(to_email: str, subject: str, html: str) -> None:
  if not GMAIL_USER or not GMAIL_APP_PASSWORD:
    raise RuntimeError("Gmail not configured. Set GMAIL_USER and GMAIL_APP_PASSWORD to send emails.")

  msg = EmailMessage()
  msg["From"] = FROM_EMAIL
  msg["To"] = to_email
  msg["Subject"] = subject
  msg.set_content("HTML email requires an HTML-capable client.")
  msg.add_alternative(html, subtype="html")

  with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=SMTP_TIMEOUT_SEC) as smtp:
    smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    smtp.send_message(msg)


class EmailDeliveryService:
  """Handles newsletter delivery and logging, mirroring the TS implementation."""

  def send_newsletters(self, ranked_events_by_user: Mapping[str, List[Dict[str, Any]]]) -> None:
    success = 0
    failed = 0

    for user_id, events in ranked_events_by_user.items():
      try:
        self.send_personalized_email(user_id, events)
        success += 1
        time.sleep(0.1)
      except Exception as exc:
        logger.error(f"Failed to send email to user {user_id}: {exc}")
        failed += 1

    logger.info(f"Email delivery complete: {success} sent, {failed} failed")

  def send_personalized_email(self, user_id: str, events: List[Dict[str, Any]]) -> None:
    user_resp = supabase.table("users").select("*").eq("id", user_id).limit(1).execute()
    ensure_ok(user_resp, action="select users")
    user = user_resp.data[0] if user_resp.data else None
    if not user:
      raise RuntimeError(f"Failed to fetch user {user_id}")

    user_email = user.get("email")
    if not user_email:
      raise RuntimeError(f"User {user_id} has no email address")
    if user.get("is_unsubscribed"):
      logger.info(f"Skipping unsubscribed user: {user_email}")
      return

    html = generate_personalized_email(user, events, FEEDBACK_URL)
    subject = f"Your Weekly Event Picks - {len(events)} Events Curated For You"

    try:
      send_email(user_email, subject, html)
      log_resp = supabase.table("email_logs").insert({
        "user_id": user_id,
        "status": "sent",
        "sent_at": datetime.now(timezone.utc).isoformat(),
      }).execute()
      try:
        ensure_ok(log_resp, action="insert email_logs (sent)")
      except Exception as log_exc:
        logger.warning(f"Failed to log email success for user {user_id}: {log_exc}")
      logger.info(f"Email sent successfully to {user_email}")
    except Exception as exc:
      log_resp = supabase.table("email_logs").insert({
        "user_id": user_id,
        "status": "failed",
        "error_message": str(exc),
        "sent_at": datetime.now(timezone.utc).isoformat(),
      }).execute()
      try:
        ensure_ok(log_resp, action="insert email_logs (failed)")
      except Exception as log_exc:
        logger.warning(f"Failed to log email failure for user {user_id}: {log_exc}")
      raise

  def send_test_email(self, to_email: str) -> None:
    html = "<h1>Test Email</h1><p>This is a test email from the Event Newsletter System.</p>"
    send_email(to_email, "Test Email - Event Newsletter System", html)
    logger.info(f"Test email sent to {to_email}")
