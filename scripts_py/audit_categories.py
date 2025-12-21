"""
Category Classification Audit Tool

Measures how accurately OpenAI categorizes events by comparing
AI classifications against human judgments.

Usage: python scripts_py/audit_categories.py [--sample 50]
"""

import json
import random
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from python_app.supabase_client import supabase, ensure_ok
from python_app.embeddings import CONNECT3_CATEGORIES

# Audit results file
AUDIT_FILE = Path(__file__).parent.parent / "category_audit_results.json"


def load_events_with_categories(limit: int = 100):
    """Load events that have been categorized."""
    resp = supabase.table("event_embeddings").select("event_id, category").limit(limit).execute()
    ensure_ok(resp, action="select event_embeddings")
    
    categorized = {e["event_id"]: e["category"] for e in (resp.data or []) if e.get("category")}
    
    # Load event details from all_posts.json
    json_path = Path(__file__).resolve().parents[1] / "all_posts.json"
    if not json_path.exists():
        print(f"Error: {json_path} not found")
        return []
    
    with open(json_path, 'r', encoding='utf-8') as f:
        posts = json.load(f)
    
    events = []
    for post in posts:
        if post["id"] in categorized:
            events.append({
                "id": post["id"],
                "caption": post.get("caption", "")[:500],  # Truncate for display
                "ai_category": categorized[post["id"]]
            })
    
    return events


def display_categories():
    """Show numbered category list."""
    print("\n📂 CATEGORIES:")
    print("-" * 40)
    for i, cat in enumerate(CONNECT3_CATEGORIES, 1):
        display_name = cat.replace("_", " ").title()
        print(f"  {i:2}. {display_name}")
    print(f"  {len(CONNECT3_CATEGORIES) + 1:2}. SKIP (unclear/ambiguous)")
    print(f"  {len(CONNECT3_CATEGORIES) + 2:2}. QUIT audit")
    print("-" * 40)


def run_audit(sample_size: int = 50):
    """Run interactive category audit."""
    print("=" * 60)
    print("  📊 CATEGORY CLASSIFICATION AUDIT")
    print("  Measuring OpenAI categorization accuracy")
    print("=" * 60)
    
    # Load events
    print("\nLoading events...")
    all_events = load_events_with_categories(limit=500)
    
    if not all_events:
        print("No categorized events found!")
        return
    
    # Random sample
    sample = random.sample(all_events, min(sample_size, len(all_events)))
    print(f"Sampled {len(sample)} events for audit\n")
    
    # Load any existing audit results
    audit_results = []
    if AUDIT_FILE.exists():
        with open(AUDIT_FILE, 'r') as f:
            audit_results = json.load(f)
        print(f"Loaded {len(audit_results)} previous audit results")
    
    # Track metrics
    correct = 0
    incorrect = 0
    skipped = 0
    confusion = defaultdict(lambda: defaultdict(int))  # confusion[ai_cat][human_cat] = count
    
    display_categories()
    
    for i, event in enumerate(sample, 1):
        print(f"\n{'='*60}")
        print(f"EVENT {i}/{len(sample)}")
        print(f"{'='*60}")
        print(f"\n📝 CAPTION:\n{event['caption'][:400]}...")
        print(f"\n🤖 AI CLASSIFIED AS: {event['ai_category'].replace('_', ' ').title()}")
        
        # Get human judgment
        while True:
            try:
                choice = input(f"\n✅ Correct category (1-{len(CONNECT3_CATEGORIES)}, {len(CONNECT3_CATEGORIES)+1}=skip, {len(CONNECT3_CATEGORIES)+2}=quit): ").strip()
                choice_num = int(choice)
                
                if choice_num == len(CONNECT3_CATEGORIES) + 2:  # Quit
                    print("\nSaving and exiting...")
                    break
                elif choice_num == len(CONNECT3_CATEGORIES) + 1:  # Skip
                    skipped += 1
                    break
                elif 1 <= choice_num <= len(CONNECT3_CATEGORIES):
                    human_category = CONNECT3_CATEGORIES[choice_num - 1]
                    ai_category = event["ai_category"]
                    
                    # Record result
                    is_correct = (human_category == ai_category)
                    if is_correct:
                        correct += 1
                        print("✓ MATCH!")
                    else:
                        incorrect += 1
                        print(f"✗ MISMATCH: AI said '{ai_category}', you said '{human_category}'")
                    
                    confusion[ai_category][human_category] += 1
                    
                    audit_results.append({
                        "event_id": event["id"],
                        "ai_category": ai_category,
                        "human_category": human_category,
                        "is_correct": is_correct,
                        "audited_at": datetime.utcnow().isoformat()
                    })
                    break
                else:
                    print(f"Please enter 1-{len(CONNECT3_CATEGORIES) + 2}")
            except ValueError:
                print("Please enter a number")
            except KeyboardInterrupt:
                print("\n\nSaving and exiting...")
                break
        else:
            continue
        
        if choice_num == len(CONNECT3_CATEGORIES) + 2:  # Quit was selected
            break
    
    # Save results
    with open(AUDIT_FILE, 'w') as f:
        json.dump(audit_results, f, indent=2)
    print(f"\n💾 Saved {len(audit_results)} audit results to {AUDIT_FILE}")
    
    # Calculate and display metrics
    print("\n" + "=" * 60)
    print("  📈 AUDIT RESULTS")
    print("=" * 60)
    
    total_judged = correct + incorrect
    if total_judged > 0:
        accuracy = (correct / total_judged) * 100
        print(f"\n  Overall Accuracy: {accuracy:.1f}%")
        print(f"  Correct: {correct}")
        print(f"  Incorrect: {incorrect}")
        print(f"  Skipped: {skipped}")
        
        # Per-category accuracy
        print("\n  PER-CATEGORY BREAKDOWN:")
        print("-" * 50)
        
        category_stats = defaultdict(lambda: {"correct": 0, "total": 0})
        for result in audit_results:
            ai_cat = result["ai_category"]
            category_stats[ai_cat]["total"] += 1
            if result["is_correct"]:
                category_stats[ai_cat]["correct"] += 1
        
        for cat in sorted(category_stats.keys()):
            stats = category_stats[cat]
            cat_accuracy = (stats["correct"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            bar = "█" * int(cat_accuracy / 5)
            print(f"  {cat:30} {cat_accuracy:5.1f}% {bar}")
        
        # Most common misclassifications
        print("\n  TOP MISCLASSIFICATIONS:")
        print("-" * 50)
        misclass = []
        for ai_cat, human_cats in confusion.items():
            for human_cat, count in human_cats.items():
                if ai_cat != human_cat:
                    misclass.append((ai_cat, human_cat, count))
        
        misclass.sort(key=lambda x: x[2], reverse=True)
        for ai_cat, human_cat, count in misclass[:5]:
            print(f"  AI: {ai_cat:25} → Should be: {human_cat:25} ({count}x)")
    else:
        print("\n  No events were judged.")


def show_summary():
    """Show summary of existing audit results."""
    if not AUDIT_FILE.exists():
        print("No audit results found. Run 'python scripts_py/audit_categories.py' to start auditing.")
        return
    
    with open(AUDIT_FILE, 'r') as f:
        results = json.load(f)
    
    if not results:
        print("No audit results recorded yet.")
        return
    
    correct = sum(1 for r in results if r["is_correct"])
    total = len(results)
    accuracy = (correct / total) * 100
    
    print("=" * 60)
    print("  📊 CATEGORY AUDIT SUMMARY")
    print("=" * 60)
    print(f"\n  Total Events Audited: {total}")
    print(f"  Overall Accuracy: {accuracy:.1f}%")
    print(f"  Correct: {correct}")
    print(f"  Incorrect: {total - correct}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Audit OpenAI category classifications")
    parser.add_argument("--sample", type=int, default=20, help="Number of events to audit")
    parser.add_argument("--summary", action="store_true", help="Show summary of existing audits")
    
    args = parser.parse_args()
    
    if args.summary:
        show_summary()
    else:
        run_audit(sample_size=args.sample)
