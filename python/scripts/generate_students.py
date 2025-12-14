"""
Generate Synthetic Students Script

Creates 100 synthetic university students with preferences.
Run: python -m python.scripts.generate_students
"""
import random
import json
from datetime import datetime
from dotenv import load_dotenv
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.supabase_client import supabase, EVENT_CATEGORIES

# Load environment variables
load_dotenv()

# Sample data
FIRST_NAMES = [
    "Emma", "Liam", "Olivia", "Noah", "Ava", "Oliver", "Sophia", "Elijah",
    "Isabella", "Lucas", "Mia", "Mason", "Charlotte", "Ethan", "Amelia",
    "James", "Harper", "Benjamin", "Evelyn", "Alexander", "Aria", "William",
    "Chloe", "Daniel", "Abigail", "Michael", "Emily", "Henry", "Elizabeth",
    "Sebastian", "Sofia", "Jack", "Avery", "Aiden", "Scarlett", "Owen"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark"
]

FACULTIES = [
    "Engineering", "Science", "Arts", "Business and Economics", "Medicine",
    "Law", "Fine Arts and Music", "Education", "Architecture"
]


def generate_preferences() -> dict:
    """Generate random user preferences"""
    prefs = {}
    for cat in EVENT_CATEGORIES:
        # Random preference between 0.2 and 0.9
        prefs[cat] = round(random.uniform(0.2, 0.9), 2)
    return prefs


def main():
    print("🎓 Generating 100 synthetic university students...\n")
    
    success_count = 0
    error_count = 0
    
    for i in range(100):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        name = f"{first_name} {last_name}"
        email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 99)}@student.unimelb.edu.au"
        faculty = random.choice(FACULTIES)
        year = random.randint(1, 5)
        
        try:
            # Insert user
            result = supabase.table("users").insert({
                "name": name,
                "email": email,
                "faculty": faculty,
                "year_level": year
            }).execute()
            
            user = result.data[0]
            user_id = user["id"]
            
            # Insert preferences
            preferences = generate_preferences()
            preferences["user_id"] = user_id
            
            supabase.table("user_preferences").insert(preferences).execute()
            
            print(f"✓ Created: {name} ({faculty}, Year {year})")
            print(f"  Email: {email}")
            success_count += 1
            
        except Exception as e:
            print(f"✗ Error creating user: {e}")
            error_count += 1
    
    print(f"\n{'='*50}")
    print(f"✅ Student generation complete!")
    print(f"   Success: {success_count}")
    print(f"   Errors: {error_count}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
