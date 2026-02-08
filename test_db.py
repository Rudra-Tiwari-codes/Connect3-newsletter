import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def init_test():
    # 1. Insert a dummy user
    user_data = {
        "email": "test_user_integration@connect3.com", 
        "name": "Integration Test User",
        "is_new_recipient": True
    }
    user = supabase.table("profiles").insert(user_data).execute()
    print(f"Created User: {user.data[0]['id']}")

    # 2. Insert a dummy event
    event_data = {
        "title": "Hackathon 2025", 
        "description": "A cool AI hackathon.", 
        "category": None  # Intentionally empty for your AI script later
    }
    event = supabase.table("events").insert(event_data).execute()
    print(f"Created Event: {event.data[0]['title']}")

    print("✅ Database connection successful!")

if __name__ == "__main__":
    init_test()
