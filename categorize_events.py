import os
import requests
import json
from supabase import create_client, Client
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize Clients
supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Gemini Config
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# Define your "Connect3" Categories
CATEGORIES = [
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
        print(f"❌ OpenAI error: {e}")
        return None

def get_category_from_gemini(title, description):
    """Try to get category using Gemini as fallback."""
    if not GEMINI_API_KEY:
        return None
        
    prompt = f"Classify the following event into EXACTLY one of these categories: {', '.join(CATEGORIES)}.\n\nEvent Title: {title}\nDescription: {description[:500]}\n\nReturn only the category name."
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(GEMINI_URL, headers={"Content-Type": "application/json"}, data=json.dumps(data))
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        else:
            print(f"❌ Gemini error: {response.status_code} - {response.text[:100]}")
            return None
    except Exception as e:
        print(f"❌ Gemini exception: {e}")
        return None

def categorize_events():
    # 1. Fetch events that need a category
    response = supabase.table("events").select("*").is_("category", "null").execute()
    events = response.data

    if not events:
        print("No uncategorized events found.")
        return

    print(f"Found {len(events)} events to categorize...")

    for event in events:
        # Try OpenAI first, then Gemini
        new_category = get_category_from_openai(event['title'], event['description'])
        
        if not new_category or new_category not in CATEGORIES:
            print(f"🔄 Retrying with Gemini for '{event['title']}'...")
            new_category = get_category_from_gemini(event['title'], event['description'])

        # 2. Update the event in Supabase
        if new_category and new_category in CATEGORIES:
            supabase.table("events").update({"category": new_category}).eq("id", event["id"]).execute()
            print(f"✅ Categorized '{event['title']}' as {new_category}")
        else:
            print(f"⚠️ Failed to categorize '{event['title']}': Invalid or missing category response.")

if __name__ == "__main__":
    categorize_events()