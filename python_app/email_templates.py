"""Simple HTML email templates for Connect3 newsletters."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote


def format_category(category: Optional[str]) -> str:
  if not category:
    return "General"
  return " ".join(word.capitalize() for word in category.split("_"))


def generate_personalized_email(user: Dict[str, Any], events: List[Dict[str, Any]], feedback_base_url: str) -> str:
  cards = []
  
  # Capture email send timestamp for time decay tracking
  email_sent_at = datetime.now(timezone.utc).isoformat()
  
  for evt in events:
    when = evt.get("event_date") or evt.get("timestamp")
    when_str = ""
    try:
      when_dt = datetime.fromisoformat(when.replace("Z", "+00:00")) if when else None
      when_str = when_dt.strftime("%B %d, %Y at %I:%M %p") if when_dt else ""
    except Exception:
      when_str = when or ""
    # Build tracking URLs - goes to tracking API which stores click then redirects to connect3.app
    # Recommender returns 'event_id', all_posts.json uses 'id'
    event_id = evt.get('event_id') or evt.get('id') or 'unknown'
    category = evt.get('category') or 'general'
    user_id = user.get('id')
    
    # Tracking API stores the interaction then redirects to clean connect3.app URL
    # Include sent timestamp for 15-day time decay enforcement
    tracking_base = "https://connect3-newsletter.vercel.app"
    sent_param = quote(email_sent_at)
    like_url = f"{tracking_base}/feedback?uid={user_id}&eid={event_id}&cat={category}&action=like&sent={sent_param}"
    dislike_url = f"{tracking_base}/feedback?uid={user_id}&eid={event_id}&cat={category}&action=dislike&sent={sent_param}"
    
    cards.append(
      f"""
      <div style="background: #fff; border-radius: 10px; padding: 16px; margin-bottom: 16px; border: 1px solid #e5e7eb;">
        <h3 style="margin: 0 0 8px 0; color: #111827;">{evt.get('title', 'Event')}</h3>
        <p style="margin: 0 0 8px 0; color: #4b5563;">{evt.get('description', '')}</p>
        <p style="margin: 0 0 12px 0; color: #6b7280; font-size: 14px;">
          <strong>When:</strong> {when_str}<br>
          <strong>Where:</strong> {evt.get('location', 'TBA')}<br>
          <strong>Category:</strong> {format_category(evt.get('category'))}
        </p>
        <div style="margin-top: 10px;">
          <a href="{like_url}" style="background: #22c55e; color: white; padding: 8px 14px; text-decoration: none; border-radius: 6px; margin-right: 8px;">Interested</a>
          <a href="{dislike_url}" style="background: #ef4444; color: white; padding: 8px 14px; text-decoration: none; border-radius: 6px;">Not interested</a>
        </div>
      </div>
      """
    )


  return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0; padding:0; background:#f3f4f6; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:640px; margin:0 auto; background:#fff;">
    <div style="background:#4f46e5; color:#fff; padding:24px; text-align:center;">
      <h1 style="margin:0;">Your Weekly Event Picks</h1>
      <p style="margin:8px 0 0 0;">Hi {user.get('name') or user.get('email') or 'there'}! We picked {len(events)} events for you.</p>
    </div>
    <div style="padding:24px;">
      {''.join(cards)}
    </div>
    <div style="background:#f9fafb; padding:16px; text-align:center; color:#6b7280; font-size:12px;">
      <p style="margin:0;">Connect3 Newsletter</p>
    </div>
  </div>
</body>
</html>
  """
