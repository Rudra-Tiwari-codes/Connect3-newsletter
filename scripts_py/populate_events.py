"""Script to populate the events table from post JSON."""
import json
import sys
from pathlib import Path

# Add parent directory to path so we can import python_app from any directory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python_app.supabase_client import supabase, ensure_ok

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_POSTS_PATH = ROOT_DIR / "all_posts_simulated.json"


def main(posts_path: Path = None) -> None:
    # Load posts
    posts_path = posts_path or DEFAULT_POSTS_PATH
    with posts_path.open('r', encoding='utf-8') as f:
        posts = json.load(f)
    print(f"Loading posts from {posts_path}")
    print(f"Found {len(posts)} posts to insert into events table")
    
    # Get categories from embeddings
    print("Fetching categories from embeddings...")
    emb_resp = supabase.table('event_embeddings').select('event_id, category').execute()
    ensure_ok(emb_resp, action='select embeddings')
    cat_map = {e['event_id']: e.get('category') for e in (emb_resp.data or [])}
    print(f"Found {len(cat_map)} embeddings with categories")
    
    # Build all events first
    print("Building events list...")
    events = []
    for post in posts:
        caption = post.get('caption', '') or ''
        event_id = str(post['id'])
        event = {
            'id': event_id,
            'name': caption[:80].split('\n')[0] if caption else 'Event',
            'description': caption[:500] if caption else '',
            'start': post.get('event_date') or post.get('timestamp') or post.get('date'),
            'category': cat_map.get(event_id) or post.get('category'),
            'thumbnail': post.get('media_url') or post.get('image_url') or post.get('image'),
            'booking_url': post.get('permalink') or post.get('source_url') or post.get('url'),
        }
        events.append(event)
    
    # Batch upsert (Supabase supports batch operations)
    print(f"Upserting {len(events)} events in batches...")
    batch_size = 50
    success = 0
    errors = 0
    
    for i in range(0, len(events), batch_size):
        batch = events[i:i+batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(events) + batch_size - 1) // batch_size
        print(f"  Batch {batch_num}/{total_batches} ({len(batch)} events)...", end=" ", flush=True)
        
        try:
            resp = supabase.table('events').upsert(batch, on_conflict='id').execute()
            success += len(batch)
            print("OK")
        except Exception as e:
            print(f"ERROR: {e}")
            errors += len(batch)
            if errors > 100:
                print("Too many errors, stopping")
                break
    
    print(f"\nInserted {success} events, {errors} errors")
    
    # Verify
    check = supabase.table('events').select('id', count='exact').execute()
    print(f"Total events in table: {check.count}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--posts", type=Path, default=DEFAULT_POSTS_PATH, help="Path to posts JSON")
    args = parser.parse_args()
    main(posts_path=args.posts)
