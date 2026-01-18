"""Simple HTML email templates for Connect3 newsletters."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlparse
import hashlib
import hmac
import html

from .config import get_env


UNSUBSCRIBE_TOKEN_SECRET = get_env("UNSUBSCRIBE_TOKEN_SECRET")


def format_category(category: Optional[str]) -> str:
  if not category:
    return "General"
  return " ".join(word.capitalize() for word in category.split("_"))


def _expected_unsubscribe_token(user_id: str, secret: str) -> str:
  mac = hmac.new(secret.encode("utf-8"), user_id.encode("utf-8"), hashlib.sha256)
  return mac.hexdigest()


def _tracking_base_from_feedback_url(feedback_base_url: str) -> str:
  parsed = urlparse(feedback_base_url)
  if parsed.scheme and parsed.netloc:
    return f"{parsed.scheme}://{parsed.netloc}"
  return "https://connect3-newsletter.vercel.app"


def generate_personalized_email(user: Dict[str, Any], events: List[Dict[str, Any]], feedback_base_url: str) -> str:
  cards = []
  
  # Capture email send timestamp for time decay tracking
  email_sent_at = datetime.now(timezone.utc).isoformat()

  tracking_base = _tracking_base_from_feedback_url(feedback_base_url)
  banner_url = get_env("NEWSLETTER_BANNER_URL") or f"{tracking_base}/assets/banner.png"
  user_id = user.get('id')

  unsubscribe_html = ""
  if user_id:
    if UNSUBSCRIBE_TOKEN_SECRET:
      token = _expected_unsubscribe_token(user_id, UNSUBSCRIBE_TOKEN_SECRET)
      unsubscribe_url = f"{tracking_base}/unsubscribe?uid={user_id}&token={token}"
    else:
      unsubscribe_url = f"{tracking_base}/unsubscribe?uid={user_id}"
    unsubscribe_html = f'<p style="margin:6px 0 0 0;"><a href="{unsubscribe_url}" style="color:#6b7280;">Unsubscribe</a></p>'
  
  for i, evt in enumerate(events):
    # Escape user content for safety
    title = html.escape(evt.get('title', 'Event'))
    location = html.escape(evt.get('location', 'TBA'))
    media_url = evt.get('media_url')
    media_html = ""
    if media_url:
      media_html = (
        f'<img src="{html.escape(media_url, quote=True)}" '
        f'alt="{title}" '
        'style="width:100%; max-width:100%; height:auto; aspect-ratio:1/1; object-fit:cover; '
        'border-radius: 8px; display:block; margin-bottom: 10px; border:0; outline:none; text-decoration:none;" />'
      )
    
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
    # Tracking API stores the interaction then redirects to clean connect3.app URL
    # Include sent timestamp for 15-day time decay enforcement
    sent_param = quote(email_sent_at)
    like_url = f"{tracking_base}/feedback?uid={user_id}&eid={event_id}&cat={category}&action=like&sent={sent_param}"
    
    
    cards.append(
      f"""
      <table role="presentation" class="card-table" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:separate; border-spacing:0; width:100%;">
        <tr>
          <td class="card" style="padding:16px; background:#F8F6FF; border:1px solid #DFCAFB; border-radius:12px; overflow:hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <!-- event-{event_id}-{i} -->
            <a href="{like_url}" style="text-decoration:none; color:inherit; display:block;">
              {media_html}
              <h3 style="margin: 0 0 8px 0; color: #111827; font-size: 18px;">{title}</h3>
              <p style="margin: 0 0 0 0; color: #6b7280; font-size: 13px;">
                <strong>When:</strong> {when_str}<br>
                <strong>Where:</strong> {location}<br>
                <strong>Category:</strong> {format_category(evt.get('category'))}
              </p>
            </a>
          </td>
        </tr>
      </table>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td height="16" style="line-height:16px; font-size:0;">&nbsp;</td>
        </tr>
      </table>
      """
    )


  return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body, table, td, a {{
      -webkit-text-size-adjust: 100%;
      -ms-text-size-adjust: 100%;
    }}
    table {{
      border-collapse: collapse;
    }}
    .card-table {{
      border-collapse: separate !important;
      border-spacing: 0 !important;
    }}
    img {{
      border: 0;
      height: auto;
      line-height: 100%;
      outline: none;
      text-decoration: none;
      -ms-interpolation-mode: bicubic;
    }}
    @media only screen and (max-width: 600px) {{
      .container {{
        width: 100% !important;
      }}
      .content {{
        padding: 12px !important;
      }}
      .header {{
        padding: 16px !important;
      }}
      .header h1 {{
        font-size: 24px !important;
      }}
      .header p {{
        font-size: 14px !important;
      }}
      .card {{
        padding: 12px !important;
      }}
      .card h3 {{
        font-size: 16px !important;
      }}
      .button {{
        display: block !important;
        width: 100% !important;
        margin: 8px 0 !important;
        text-align: center !important;
        box-sizing: border-box !important;
      }}
    }}
  </style>
</head>
<body style="margin:0; padding:0; background:#ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; width:100%;">
  <div style="display:none; font-size:1px; line-height:1px; max-height:0; max-width:0; opacity:0; overflow:hidden;">
    {len(events)} curated events just for you this week
  </div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;">
    <tr>
      <td align="center">
        <table role="presentation" class="container" width="100%" cellpadding="0" cellspacing="0" style="max-width:640px; width:100%; margin:0 auto; background:#fff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
          <tr>
            <td class="content" style="padding:24px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
                <tr>
                  <td class="header" background="{banner_url}" bgcolor="#111827" style="background:#111827 url('{banner_url}') center/cover no-repeat; color:#fff; padding:24px; text-align:center; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                    <h1 style="margin:0; color:#FFFFFF; font-weight:700; font-size: 28px;">Your Weekly Event Picks</h1>
                    <p style="margin:8px 0 0 0; color:#FFFFFF; font-size: 16px;">Hi {html.escape(user.get('name') or user.get('email') or 'there')}! Here are {len(events)} events picked for you.</p>
                  </td>
                </tr>
              </table>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="padding-top:24px;">
                    {''.join(cards)}
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="background:#f9fafb; padding:16px; text-align:center; color:#6b7280; font-size:12px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
              <p style="margin:0;">Connect3 Newsletter</p>
              {unsubscribe_html}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
  """
