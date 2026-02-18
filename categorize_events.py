"""Fallback for uncategorized events.

Automatically assign a single, fixed category to uncategorized events in
Supabase, using OpenAI first and Gemini as a fallback if OpenAI fails or
gives an invalid answer.
"""

import json
import logging
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import OpenAI
from supabase import Client, create_client

# Allow importing python_app when running as a standalone script
sys.path.insert(0, str(Path(__file__).resolve().parent))

from python_app.categories import CONNECT3_CATEGORIES

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize Clients
_supabase_url = os.environ.get("SUPABASE_URL")
_supabase_key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
if not _supabase_url or not _supabase_key:
    logger.warning("Supabase env vars not set — standalone categorize_events will fail.")
    supabase: Client | None = None
else:
    supabase: Client = create_client(_supabase_url, _supabase_key)

openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Gemini Config — key is only included in the request at call time to avoid
# leaking it in tracebacks or logs at module-load.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# Re-use the authoritative categories list from python_app.categories
CATEGORIES = list(CONNECT3_CATEGORIES)

class EventClassifier:
    def __init__(self):
        self.categories = CATEGORIES

    def classify_event(self, title, description):
        new_category = get_category_from_openai(title, description)

        if not new_category or new_category not in self.categories:
            new_category = get_category_from_gemini(title, description)

        if new_category in self.categories:
            return new_category

        return None

    def classify_batch(self, events):
        classifications = {}
        for event in events:
            title = event.get("name") or event.get("title") or ""
            description = event.get("description") or ""
            category = self.classify_event(title, description)
            if category:
                classifications[event["id"]] = category
        return classifications

def get_category_from_openai(title, description):
    """Try to get category using OpenAI."""
    prompt = f"Classify the following event into EXACTLY one of these categories: {', '.join(CATEGORIES)}.\n\nEvent Title: {title}\nDescription: {description[:500]}\n\nReturn only the category name."
    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error("OpenAI classification error: %s", e)
        return None

def get_category_from_gemini(title, description):
    """Try to get category using Gemini as fallback."""
    if not GEMINI_API_KEY:
        return None
        
    prompt = f"Classify the following event into EXACTLY one of these categories: {', '.join(CATEGORIES)}.\n\nEvent Title: {title}\nDescription: {description[:500]}\n\nReturn only the category name."
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(
            GEMINI_ENDPOINT,
            headers={"Content-Type": "application/json"},
            params={"key": GEMINI_API_KEY},
            data=json.dumps(data),
        )
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        else:
            logger.error("Gemini error: %d - %s", response.status_code, response.text[:100])
            return None
    except Exception as e:
        logger.error("Gemini exception: %s", e)
        return None

def categorize_events():
    if supabase is None:
        logger.error("Supabase client not available — cannot categorize events.")
        return

    # 1. Fetch events that need a category
    response = supabase.table("events").select("*").is_("category", "null").execute()
    events = response.data

    if not events:
        logger.info("No uncategorized events found.")
        return

    logger.info("Found %d events to categorize...", len(events))

    classifier = EventClassifier()
    classifications = classifier.classify_batch(events)

    for event in events:
        event_id = event["id"]
        new_category = classifications.get(event_id)
        if new_category:
            supabase.table("events").update({"category": new_category}).eq("id", event_id).execute()
            logger.info("Categorized '%s' as %s", event.get('name', event_id), new_category)
        else:
            logger.warning("Failed to categorize '%s': Invalid or missing category response.", event.get('name', event_id))

if __name__ == "__main__":
    categorize_events()
