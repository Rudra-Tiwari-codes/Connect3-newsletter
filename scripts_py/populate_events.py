"""Script to populate the events table from all_posts.json"""
import json
import sys
from pathlib import Path

# Add parent directory to path so we can import python_app from any directory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python_app.supabase_client import supabase, ensure_ok

def main():
    # Load posts
    with open('all_posts.json', 'r', encoding='utf-8') as f:
        posts = json.load(f)
    print(f"Found {len(posts)} posts to insert into events table")
    
    # Get categories from embeddings
    emb_resp = supabase.table('event_embeddings').select('event_id, category').execute()
    ensure_ok(emb_resp, action='select embeddings')
    cat_map = {e['event_id']: e.get('category') for e in (emb_resp.data or [])}
    print(f"Found {len(cat_map)} embeddings with categories")
    
    # Insert events with minimal fields that the table supports
    success = 0
    errors = 0
    for post in posts:
        event = {
            'id': post['id'],
            'event_date': post.get('timestamp'),
            'category': cat_map.get(post['id']),
        }
        try:
            resp = supabase.table('events').upsert(event, on_conflict='id').execute()
            success += 1
        except Exception as e:
            print(f"Error on event {post['id']}: {e}")
            errors += 1
            if errors > 3:
                print("Too many errors, stopping")
                break
    
    print(f"Inserted {success} events, {errors} errors")
    
    # Verify
    check = supabase.table('events').select('id').limit(5).execute()
    print(f"Events in table now: {len(check.data) if check.data else 0}")

if __name__ == "__main__":
    main()
