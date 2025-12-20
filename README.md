# Connect3 - Event Recommendation System

Personalized university event newsletter system built for DSCubed at the University of Melbourne.

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
│  - User clicks "Interested" / "Not interested" buttons      │
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

