"""Simple HTML email templates for Connect3 newsletters."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlparse
import hashlib
import hmac
import html

from .config import get_env


UNSUBSCRIBE_TOKEN_SECRET = get_env("UNSUBSCRIBE_TOKEN_SECRET")
DEFAULT_BANNER_URL = "https://nsjrzxbtxsqmsdgevszv.supabase.co/storage/v1/object/public/newsletter-assets/banner.png"


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


def _normalize_text(value: Optional[str]) -> str:
  if not value:
    return ""
  return " ".join(str(value).split())


def _truncate_text(value: str, max_len: int) -> str:
  if len(value) <= max_len:
    return value
  trimmed = value[:max_len]
  if " " in trimmed:
    trimmed = trimmed.rsplit(" ", 1)[0]
    if not trimmed:
      trimmed = value[:max_len]
  return trimmed.rstrip() + "..."


def _event_title(evt: Dict[str, Any]) -> str:
  title = evt.get("name") or evt.get("title")
  if not title:
    fallback = evt.get("caption") or evt.get("description") or ""
    title = fallback.split("\n", 1)[0]
  title = _normalize_text(title)
  return title or "Event"


def _event_description(evt: Dict[str, Any], max_len: int = 280) -> str:
  description = evt.get("description") or evt.get("caption") or ""
  description = _normalize_text(description)
  if not description:
    return ""
  return _truncate_text(description, max_len)


def _event_media_url(evt: Dict[str, Any]) -> Optional[str]:
  return (
    evt.get("thumbnail")
    or evt.get("media_url")
    or evt.get("image_url")
    or evt.get("image")
  )


def _parse_event_datetime(value: Any) -> Optional[datetime]:
  if not value:
    return None
  if isinstance(value, datetime):
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
  if isinstance(value, str):
    try:
      parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
      return None
    if parsed.tzinfo is None:
      return parsed.replace(tzinfo=timezone.utc)
    return parsed
  return None


def _event_time_range(evt: Dict[str, Any]) -> tuple[Optional[datetime], Optional[datetime], Optional[str], Optional[str]]:
  start_raw = (
    evt.get("start")
    or evt.get("event_date")
    or evt.get("timestamp")
    or evt.get("date")
    or evt.get("created_at")
  )
  end_raw = evt.get("end") or evt.get("end_time") or evt.get("end_date")
  return _parse_event_datetime(start_raw), _parse_event_datetime(end_raw), start_raw, end_raw


def _event_location(evt: Dict[str, Any]) -> str:
  if evt.get("is_online") is True:
    return "Online"
  for key in ("location", "location_name", "venue", "address"):
    value = evt.get(key)
    if value:
      return str(value)
  return "TBA"


def generate_personalized_email(user: Dict[str, Any], events: List[Dict[str, Any]], feedback_base_url: str) -> str:
  cards = []
  
  # Capture email send timestamp for time decay tracking
  email_sent_at = datetime.now(timezone.utc).isoformat()

  tracking_base = _tracking_base_from_feedback_url(feedback_base_url)
  banner_url = get_env("NEWSLETTER_BANNER_URL") or DEFAULT_BANNER_URL
  user_id = user.get('id')
  first_name = _normalize_text(user.get("first_name"))
  if not first_name:
    full_name = _normalize_text(user.get("name"))
    if full_name:
      first_name = full_name.split(" ", 1)[0]
  greeting_name = first_name or _normalize_text(user.get("email")) or "there"

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
    title = html.escape(_event_title(evt))
    description = html.escape(_event_description(evt))
    location = html.escape(_event_location(evt))
    media_url = _event_media_url(evt)

    media_html = ""
    if media_url:
      media_html = (
        f'<img src="{html.escape(media_url, quote=True)}" '
        f'alt="{title}" '
        'style="width:100%; max-width:100%; height:auto; aspect-ratio:1/1; object-fit:cover; '
        'border-radius: 8px; display:block; margin-bottom: 10px; border:0; outline:none; text-decoration:none;" />'
      )
    
    when_str = ""
    start_dt, end_dt, start_raw, end_raw = _event_time_range(evt)
    if start_dt and end_dt:
      if start_dt.date() == end_dt.date():
        when_str = f"{start_dt.strftime('%B %d, %Y at %I:%M %p')} - {end_dt.strftime('%I:%M %p')}"
      else:
        when_str = f"{start_dt.strftime('%B %d, %Y at %I:%M %p')} - {end_dt.strftime('%B %d, %Y at %I:%M %p')}"
    elif start_dt:
      when_str = start_dt.strftime("%B %d, %Y at %I:%M %p")
    elif end_dt:
      when_str = end_dt.strftime("%B %d, %Y at %I:%M %p")
    else:
      when_str = start_raw or end_raw or ""
    if not when_str:
      when_str = "TBA"
    
    # Build tracking URLs - goes to tracking API which stores click then redirects to connect3.app
    # Recommender returns 'event_id', all_posts.json uses 'id'
    event_id = evt.get('event_id') or evt.get('id') or 'unknown'
    category = evt.get('category') or 'general'
    # Tracking API stores the interaction then redirects to clean connect3.app URL
    # Include sent timestamp for 15-day time decay enforcement
    sent_param = quote(email_sent_at)
    like_url = f"{tracking_base}/feedback?uid={user_id}&eid={event_id}&cat={category}&action=like&sent={sent_param}"

    group_title = evt.get("group_title")
    group_action_label = evt.get("group_action_label")
    group_action_event_id = evt.get("group_action_event_id") or event_id
    group_action_category = evt.get("group_action_category") or category
    group_header_html = ""
    if group_title:
      action_html = ""
      if group_action_label:
        dislike_url = (
          f"{tracking_base}/feedback?uid={user_id}&eid={group_action_event_id}"
          f"&cat={group_action_category}&action=dislike&sent={sent_param}"
        )
        action_html = (
          f'<a href="{dislike_url}" '
          'style="font-size:12px; color:#111111; background:#DFCAFB; '
          'padding:4px 10px; border-radius:999px; text-decoration:none; display:inline-block;">'
          f'{html.escape(str(group_action_label))}'
          '</a>'
        )
      group_header_html = f"""
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
        <tr>
          <td style="padding:0 0 8px 0; font-size:16px; font-weight:600; color:#111827;">
            {html.escape(str(group_title))}
          </td>
          <td align="right" style="padding:0 0 8px 0;">
            {action_html}
          </td>
        </tr>
      </table>
      """
    
    cards.append(
      f"""
      {group_header_html}
      <table role="presentation" class="card-table" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:separate; border-spacing:0; width:100%;">
        <tr>
          <td class="card" style="padding:16px; background:#F8F6FF; border:1px solid #DFCAFB; border-radius:12px; overflow:hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <!-- event-{event_id}-{i} -->
            <a href="{like_url}" style="text-decoration:none; color:inherit; display:block;">
              {media_html}
              <h3 style="margin: 0 0 8px 0; color: #111827; font-size: 18px;">{title}</h3>
              <p style="margin: 0 0 8px 0; color: #4b5563; font-size: 14px; line-height: 20px;">{description}</p>
              <p style="margin: 0 0 0 0; color: #6b7280; font-size: 13px; line-height: 18px;">
                <span style="font-weight:600; font-size:13px; line-height:18px;">When:</span>
                <span style="font-size:13px; line-height:18px;"> {when_str}</span><br>
                <span style="font-weight:600; font-size:13px; line-height:18px;">Where:</span>
                <span style="font-size:13px; line-height:18px;"> {location}</span><br>
                <span style="font-weight:600; font-size:13px; line-height:18px;">Category:</span>
                <span style="font-size:13px; line-height:18px;"> {format_category(evt.get('category'))}</span>
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
    .banner-img {{
      width: 100%;
      max-width: 640px;
      height: auto;
      display: block;
    }}
    @media only screen and (max-width: 600px) {{
      .container {{
        width: 100% !important;
      }}
      .content {{
        padding: 12px !important;
      }}
      .header {{
        padding: 0 !important;
      }}
      .header h1 {{
        font-size: 24px !important;
      }}
      .header p {{
        font-size: 14px !important;
      }}
      .banner-img {{
        width: 100% !important;
        max-width: 100% !important;
        height: auto !important;
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
                  <td class="header" bgcolor="#ffffff" style="background:#ffffff; color:#111827; padding:0; text-align:center; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
                      <tr>
                        <td align="center" style="padding:0; text-align:center;">
                          <img src="{banner_url}" alt="Connect3 Newsletter" width="640" class="banner-img" style="width:100%; max-width:640px; height:auto; display:block; border:0; outline:none; text-decoration:none;" />
                        </td>
                      </tr>
                      <tr>
                        <td align="center" style="padding:20px 24px 24px; text-align:center;">
                          <p style="margin:0; color:#4b5563; font-size:16px;">
                        Hello {html.escape(greeting_name)}, here are {len(events)} events happening this month that we think you’ll like.
                          </p>
                        </td>
                      </tr>
                    </table>
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
