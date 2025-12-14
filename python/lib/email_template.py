"""
Email Template Service for Connect3

Generates HTML email templates for personalized newsletters
"""
from typing import List, Dict, Any
from datetime import datetime
from jinja2 import Template


# Simple email template
EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Event Picks</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; }
        .content { padding: 20px; }
        .event { border: 1px solid #eee; border-radius: 8px; margin-bottom: 16px; overflow: hidden; }
        .event-header { background: #f8f9fa; padding: 12px 16px; border-bottom: 1px solid #eee; }
        .event-title { font-weight: 600; color: #333; margin: 0; }
        .event-category { font-size: 12px; color: #667eea; text-transform: uppercase; }
        .event-body { padding: 16px; }
        .event-desc { color: #666; line-height: 1.5; }
        .event-meta { display: flex; gap: 16px; margin-top: 12px; font-size: 14px; color: #888; }
        .feedback-btns { margin-top: 12px; }
        .btn { display: inline-block; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 14px; margin-right: 8px; }
        .btn-like { background: #28a745; color: white; }
        .btn-dislike { background: #dc3545; color: white; }
        .footer { padding: 20px; text-align: center; color: #888; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 Your Event Picks</h1>
            <p>Hi {{ user_name }}, here are events curated just for you!</p>
        </div>
        <div class="content">
            {% for event in events %}
            <div class="event">
                <div class="event-header">
                    <p class="event-category">{{ event.category or 'Event' }}</p>
                    <h3 class="event-title">{{ event.title }}</h3>
                </div>
                <div class="event-body">
                    <p class="event-desc">{{ event.description[:200] }}{% if event.description|length > 200 %}...{% endif %}</p>
                    <div class="event-meta">
                        {% if event.event_date %}<span>📅 {{ event.event_date[:10] }}</span>{% endif %}
                        {% if event.location %}<span>📍 {{ event.location }}</span>{% endif %}
                    </div>
                    <div class="feedback-btns">
                        <a href="{{ feedback_url }}?user_id={{ user_id }}&event_id={{ event.id }}&action=like" class="btn btn-like">👍 Interested</a>
                        <a href="{{ feedback_url }}?user_id={{ user_id }}&event_id={{ event.id }}&action=dislike" class="btn btn-dislike">👎 Not for me</a>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
        <div class="footer">
            <p>Connect3 - Personalized Event Recommendations</p>
            <p>Your feedback helps us improve recommendations!</p>
        </div>
    </div>
</body>
</html>
"""


class EmailTemplateService:
    """Service for generating HTML email templates"""
    
    def __init__(self):
        self.template = Template(EMAIL_TEMPLATE)
    
    def generate_personalized_email(
        self, 
        user: Dict[str, Any], 
        events: List[Dict[str, Any]], 
        feedback_url: str
    ) -> str:
        """Generate personalized HTML email for a user"""
        return self.template.render(
            user_name=user.get("name") or user.get("email", "").split("@")[0],
            user_id=user["id"],
            events=events,
            feedback_url=feedback_url
        )
    
    def generate_text_email(
        self, 
        user: Dict[str, Any], 
        events: List[Dict[str, Any]]
    ) -> str:
        """Generate plain text version of email"""
        user_name = user.get("name") or user.get("email", "").split("@")[0]
        
        lines = [
            f"Hi {user_name}!",
            "",
            "Here are events curated just for you:",
            ""
        ]
        
        for i, event in enumerate(events, 1):
            lines.append(f"{i}. {event.get('title', 'Event')}")
            if event.get("category"):
                lines.append(f"   Category: {event['category']}")
            if event.get("event_date"):
                lines.append(f"   Date: {event['event_date'][:10]}")
            if event.get("location"):
                lines.append(f"   Location: {event['location']}")
            lines.append("")
        
        lines.extend([
            "---",
            "Connect3 - Personalized Event Recommendations"
        ])
        
        return "\n".join(lines)


# Singleton instance
email_template_service = EmailTemplateService()
