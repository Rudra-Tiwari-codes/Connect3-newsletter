"""
Demo Local Script

Runs a local demo without database access using mock data.
Run: python -m python.scripts.demo_local
"""
from datetime import datetime, timedelta
import random

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Mock data
MOCK_EVENTS = [
    {"id": "1", "title": "AI/ML Workshop", "category": "tech_workshop", "description": "Learn about the latest in AI and machine learning"},
    {"id": "2", "title": "Networking Night", "category": "career_networking", "description": "Connect with industry professionals"},
    {"id": "3", "title": "Datathon 2025", "category": "hackathon", "description": "48-hour data science competition"},
    {"id": "4", "title": "Bar Night Social", "category": "social_event", "description": "Casual drinks and socializing"},
    {"id": "5", "title": "SWOTVAC Study Session", "category": "academic_revision", "description": "Group study for finals"},
    {"id": "6", "title": "Startup Pitch Night", "category": "entrepreneurship", "description": "Watch founders pitch their ideas"},
    {"id": "7", "title": "Sports Day", "category": "sports_recreation", "description": "Annual inter-faculty sports competition"},
    {"id": "8", "title": "Industry Talk: Google", "category": "industry_talk", "description": "Insights from Google engineers"},
]

MOCK_USERS = [
    {"id": "u1", "name": "Alice", "email": "alice@student.unimelb.edu.au", "interests": ["tech_workshop", "hackathon", "career_networking"]},
    {"id": "u2", "name": "Bob", "email": "bob@student.unimelb.edu.au", "interests": ["social_event", "sports_recreation"]},
    {"id": "u3", "name": "Charlie", "email": "charlie@student.unimelb.edu.au", "interests": ["entrepreneurship", "industry_talk", "career_networking"]},
]


def calculate_match_score(user_interests: list, event_category: str) -> float:
    """Calculate how well an event matches user interests"""
    if event_category in user_interests:
        return random.uniform(0.7, 0.95)
    return random.uniform(0.3, 0.5)


def get_recommendations_for_user(user: dict, events: list, top_n: int = 5) -> list:
    """Get top N recommendations for a user"""
    scored_events = []
    
    for event in events:
        score = calculate_match_score(user["interests"], event["category"])
        scored_events.append({
            **event,
            "score": score,
            "reason": f"Based on your interest in {event['category'].replace('_', ' ')}"
        })
    
    # Sort by score
    scored_events.sort(key=lambda e: e["score"], reverse=True)
    return scored_events[:top_n]


def main():
    print("=" * 60)
    print("🎯 Connect3 Demo - Local Mode (No Database)")
    print("=" * 60)
    print()
    
    for user in MOCK_USERS:
        print(f"👤 User: {user['name']} ({user['email']})")
        print(f"   Interests: {', '.join(user['interests'])}")
        print()
        
        recommendations = get_recommendations_for_user(user, MOCK_EVENTS)
        
        print("   📋 Top Recommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec['title']} [{rec['category']}]")
            print(f"      Score: {rec['score']:.2f} - {rec['reason']}")
        
        print()
        print("-" * 60)
        print()
    
    print("✅ Demo complete!")
    print()
    print("💡 To use with real data, run:")
    print("   python -m python.scripts.run_recommendations")


if __name__ == "__main__":
    main()
