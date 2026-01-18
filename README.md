# Connect3 - Event Recommendation System

[![Tests](https://github.com/Rudra-Tiwari-codes/Connect3-newsletter/actions/workflows/test.yml/badge.svg)](https://github.com/Rudra-Tiwari-codes/Connect3-newsletter/actions/workflows/test.yml)

Personalized university event newsletter system built for DSCubed at the University of Melbourne.

**Created by Nirav and Rudra**

## Features

- **AI-Powered Event Categorization** using GPT-4o-mini
- **Two-Tower Recommendations** using OpenAI embeddings (semantic matching)
- **Two-Phase Newsletter System** - discovery phase + personalized recommendations
- **NumPy-Accelerated Vector Search** for fast similarity matching
- **Personalized HTML Newsletters** with 9 diverse events per email

## Tech Stack

| Component | Technology |
|-----------|------------|
| Database | Supabase (Postgres) |
| Backend | Python 3.12 |
| Embeddings | OpenAI text-embedding-3-small (1536 dims) |
| Classification | GPT-4o-mini |
| Email | Gmail SMTP |
| Vector Search | NumPy (optimized) |

## Prerequisites

- Python >= 3.12
- Supabase project
- OpenAI API key
- Gmail account with App Password

## Setup

1. Create virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Set: SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY, GMAIL_USER, GMAIL_APP_PASSWORD
```

> Never commit `.env` with real credentials.

## Main Scripts

| Script | Description |
|--------|-------------|
| `categorize_events.py` | Categorize uncategorized events using AI |
| `test_db.py` | Test database connection with sample data |

## Pipeline Scripts (scripts_py/)

| Script | Description |
|--------|-------------|
| `two_phase_newsletter.py` | **Main newsletter workflow** - Phase 1: random discovery, Phase 2: personalized |
| `embed_events.py` | Generate embeddings for events from `all_posts.json` |
| `populate_events.py` | Populate events table from JSON data |
| `ingest_events.py` | Classify uncategorized events in batch |

## Two-Phase Newsletter Flow

```
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1: DISCOVERY                                         │
│  - Send 9 random events to each user                        │
│  - User clicks "Interested" button                          │
│  - Feedback stored in interactions table                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
                      (5-minute wait)
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  PHASE 2: PERSONALIZED                                      │
│  - Analyze user's Phase 1 interactions                      │
│  - Send 9 events based on preferences (3-3-1-2 split):      │
│    • 3 from top category                                    │
│    • 3 from 2nd category                                    │
│    • 1 from 3rd category                                    │
│    • 2 random for exploration                               │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
├── categorize_events.py    # Main: AI event categorization
├── test_db.py              # Main: Database connection test
├── python_app/             # Core library modules
│   ├── config.py           # Configuration management
│   ├── embeddings.py       # OpenAI embeddings
│   ├── recommender.py      # Two-Tower recommendation engine
│   ├── vector_index.py     # NumPy-optimized vector similarity search
│   ├── email_sender.py     # Email delivery service
│   ├── email_templates.py  # HTML email templates
│   ├── supabase_client.py  # Database client
│   └── openai_client.py    # OpenAI API client
├── scripts_py/             # Pipeline automation scripts
│   └── two_phase_newsletter.py  # Main newsletter workflow
├── api/                    # Vercel serverless functions
│   └── feedback.py         # Click tracking endpoint
├── tests/                  # Unit tests for python_app
├── all_posts.json          # Event data source
└── requirements.txt        # Python dependencies
```

## Quick Start

```bash
# 1. Generate embeddings for events
python scripts_py/embed_events.py

# 2. Categorize events using AI
python categorize_events.py

# 3. Run the two-phase newsletter
python scripts_py/two_phase_newsletter.py
```

## Real-Time Testing Guide

### Prerequisites Checklist

Before testing, ensure you have:

1. **Environment configured** (`.env` file with all keys)
2. **Database ready** - Run `database/migrate_tables.sql` in Supabase SQL Editor
3. **At least one user** in the `users` table with a valid email
4. **Events embedded** - Run `python scripts_py/embed_events.py` at least once

### Step 1: Test Database Connection

```bash
python test_db.py
```
✅ Should show "Connection successful" and sample data

### Step 2: Test Event Embeddings

```bash
# Generate embeddings for all events in all_posts.json
python scripts_py/embed_events.py
```
✅ Should show "Embedded X events" without errors

### Step 3: Test Event Categorization

```bash
# Categorize any uncategorized events using GPT-4o-mini
python categorize_events.py
```
✅ Should categorize events or say "No uncategorized events found"

### Step 4: Test Email Sending (Single Email)

```python
# In Python REPL or a test script:
from python_app.email_sender import EmailDeliveryService
EmailDeliveryService().send_test_email("your@email.com")
```
✅ Check your inbox for "Test Email - Event Newsletter System"

### Step 5: Full Two-Phase Newsletter Test

```bash
# Run the complete two-phase flow (default 5-minute wait)
python scripts_py/two_phase_newsletter.py

# Or with shorter wait time for testing (1 minute)
python -c "from scripts_py.two_phase_newsletter import run_two_phase_newsletter; run_two_phase_newsletter(delay_minutes=1)"
```

**Expected Output:**
```
Loaded X events from all_posts.json
CategoryCache: Loaded X categories in 1 query

==================================================
PHASE 1: INITIAL DISCOVERY (Random Events)
==================================================

Processing: user@example.com
  Cleared previous interactions for user abc-123
  Phase 1 sent: 9 random events

==================================================
WAITING 5 MINUTES FOR USER TO SELECT PREFERENCES...
==================================================
(Click 'Interested' on events you like in the email!)
  Time remaining: 5m 0s
  ...

==================================================
PHASE 2: PREFERENCE-BASED NEWSLETTER
==================================================

Processing: user@example.com
  User's preferred categories: ['tech_innovation', 'career_networking', 'academic_workshops']
  Stored top categories: ['tech_innovation', 'career_networking', 'academic_workshops']
  - 3 from tech_innovation
  - 3 from career_networking
  - 1 from academic_workshops
  - 2 exploration from: ['sports_fitness', 'arts_music']
  Phase 2 sent: Personalized events

==================================================
TWO-PHASE NEWSLETTER COMPLETE!
==================================================
```

### Step 6: Verify in Database

After running, check Supabase:

```sql
-- Check interactions were recorded
SELECT * FROM interactions ORDER BY created_at DESC LIMIT 10;

-- Check user's top categories were stored
SELECT id, email, top_categories FROM users;

-- Check email logs
SELECT * FROM email_logs ORDER BY sent_at DESC LIMIT 10;
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "Gmail not configured" | Set `GMAIL_USER` and `GMAIL_APP_PASSWORD` in `.env` |
| "No users found" | Add a user to the `users` table in Supabase |
| "No embeddings" | Run `python scripts_py/embed_events.py` first |
| Emails not arriving | Check spam folder; verify Gmail App Password is correct |

## Event Categories

Events are classified into 13 categories:
- `academic_workshops` | `career_networking` | `social_cultural`
- `sports_fitness` | `arts_music` | `tech_innovation`
- `volunteering_community` | `food_dining` | `travel_adventure`
- `health_wellness` | `entrepreneurship` | `environment_sustainability`
- `gaming_esports`

## Running Tests

```bash
pytest tests/ -v
```

## License

MIT
