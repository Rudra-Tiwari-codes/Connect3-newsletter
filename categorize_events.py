import os
from supabase import create_client, Client
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize Clients
supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
ai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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

def categorize_events():
    # 1. Fetch events that need a category
    response = supabase.table("events").select("*").is_("category", "null").execute()
    events = response.data

    if not events:
        print("No uncategorized events found.")
        return

    print(f"Found {len(events)} events to categorize...")

    for event in events:
        prompt = f"""
        Classify the following event into EXACTLY one of these categories: {', '.join(CATEGORIES)}.
        
        Event Title: {event['title']}
        Description: {event['description'][:500]}
        
        Return only the category name.
        """

        completion = ai_client.chat.completions.create(
            model="gpt-4o-mini", # Fast and cheap for this task
            messages=[{"role": "user", "content": prompt}]
        )

        new_category = completion.choices[0].message.content.strip()
        
        # 2. Update the event in Supabase
        if new_category in CATEGORIES:
            supabase.table("events").update({"category": new_category}).eq("id", event["id"]).execute()
            print(f"✅ Categorized '{event['title']}' as {new_category}")
        else:
            print(f"⚠️ OpenAI returned an invalid category: {new_category}")

if __name__ == "__main__":
    categorize_events()