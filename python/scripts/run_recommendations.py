"""
Run Recommendations Script

Generates personalized recommendations for all users.
Run: python -m python.scripts.run_recommendations
"""
import argparse
from dotenv import load_dotenv
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.supabase_client import supabase
from lib.recommender import recommender
from lib.email_delivery import email_delivery_service

# Load environment variables
load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Generate recommendations")
    parser.add_argument("--send", action="store_true", help="Send emails after generating")
    parser.add_argument("--limit", type=int, default=10, help="Number of users to process")
    args = parser.parse_args()
    
    print("🎯 Starting Two-Tower Recommendation Pipeline")
    print(f"   Mode: {'Generate and Send' if args.send else 'Generate Only (dry run)'}")
    print()
    
    # Load event embeddings
    print("📚 Loading event embeddings...")
    recommender.load_event_index()
    print(f"Loaded {recommender.event_index.size()} events into vector index")
    
    # Fetch users
    print("👤 Fetching users...")
    result = supabase.table("users").select("id, email, name").limit(args.limit).execute()
    users = result.data or []
    print(f"   Found {len(users)} users")
    print()
    
    # Generate recommendations for each user
    recommendations_by_user = {}
    
    for user in users:
        try:
            recs = recommender.get_recommendations(user["id"])
            recommendations_by_user[user["id"]] = [
                {
                    "id": r.event_id,
                    "title": r.title,
                    "category": r.category,
                    "score": r.final_score
                }
                for r in recs
            ]
            print(f"Processing {user.get('name', user['email'])}... ✓ {len(recs)} recommendations")
        except Exception as e:
            print(f"Processing {user.get('name', user['email'])}... ✗ Error: {e}")
            recommendations_by_user[user["id"]] = []
    
    print()
    print(f"📊 Generated recommendations for {len(users)} users")
    
    # Send emails if requested
    if args.send:
        print()
        print("📧 Sending emails...")
        result = email_delivery_service.send_newsletters(recommendations_by_user)
        print(f"   Sent: {result['success']}, Failed: {result['failure']}")
    
    print()
    print("✅ Recommendation pipeline complete!")


if __name__ == "__main__":
    main()
