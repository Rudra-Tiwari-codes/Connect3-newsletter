"""AI-powered event classifier for Connect3."""

from typing import Dict, List

from .openai_client import client, with_retry

EVENT_CATEGORIES: List[str] = [
  "academic_workshops",
  "career_networking",
  "social_cultural",
  "sports_fitness",
  "arts_music",
  "tech_innovation",
  "volunteering_community",
  "food_dining",
  "travel_adventure",
  "health_wellness",
  "entrepreneurship",
  "environment_sustainability",
  "gaming_esports",
]

DEFAULT_CATEGORY = "academic_workshops"


class EventClassifier:
  """Classify events into the predefined EVENT_CATEGORIES."""

  def classify_event(self, event: Dict[str, str]) -> str:
    prompt = f"""Classify this university event into ONE of these categories:
{", ".join(EVENT_CATEGORIES)}

Event Title: {event.get("title") or "No title"}
Event Description: {event.get("description") or "No description"}
Event Location: {event.get("location") or "No location"}

Respond with ONLY the category name, nothing else."""

    try:
      def _call():
        return client.chat.completions.create(
          model="gpt-4o-mini",
          messages=[
            {
              "role": "system",
              "content": "You are an event classification assistant. Respond with only the category name.",
            },
            {"role": "user", "content": prompt},
          ],
          temperature=0.3,
          max_tokens=50,
        )

      resp = with_retry(_call, label="OpenAI event classification")
      category = (resp.choices[0].message.content or "").strip().lower()
      if self._is_valid_category(category):
        return category
      print(f"Invalid category returned: {category}, defaulting to {DEFAULT_CATEGORY}")
    except Exception as exc:
      print(f"Error classifying event {event.get('id')}: {exc}")

    return DEFAULT_CATEGORY

  def classify_batch(self, events: List[Dict[str, str]]) -> Dict[str, str]:
    results: Dict[str, str] = {}
    for event in events:
      category = self.classify_event(event)
      event_id = event.get("id")
      if not event_id:
        continue
      results[event_id] = category
    return results

  def _is_valid_category(self, category: str) -> bool:
    return category in EVENT_CATEGORIES
