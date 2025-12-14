from python_app.email_templates import generate_personalized_email


def test_generate_personalized_email_contains_user_and_events():
  user = {"id": "u1", "email": "test@example.com", "name": "Test User"}
  events = [
    {"id": "e1", "title": "Event 1", "description": "Desc", "event_date": "2025-01-01T00:00:00Z", "location": "Campus", "category": "tech_innovation"}
  ]
  html = generate_personalized_email(user, events, "http://example.com/feedback")
  assert "Event 1" in html
  assert "Test User" in html
  assert "Interested" in html
