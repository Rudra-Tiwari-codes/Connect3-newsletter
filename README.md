# Connect3 - Event Recommendation System

Personalized university event newsletter system built for DSCubed at the University of Melbourne.

## Features

- **AI-Powered Event Categorization** using GPT-4o-mini
- **Two-Tower Recommendations** using OpenAI embeddings (semantic matching)
- **Personalized HTML Newsletters** with 9 diverse events per email
- **Vector-based User Matching** for preference learning

## Tech Stack

| Component | Technology |
|-----------|------------|
| Database | Supabase (Postgres) |
| Backend | Python 3.12 |
| Embeddings | OpenAI text-embedding-3-small (1536 dims) |
| Classification | GPT-4o-mini |
| Email | Gmail SMTP |

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
# Set: SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY, SENDER_EMAIL, GMAIL_APP_PASSWORD
```

> Never commit `.env` with real credentials.

## Main Scripts

| Script | Description |
|--------|-------------|
| `categorize_events.py` | Categorize uncategorized events using AI |
| `generate_newsletter.py` | Generate and send newsletter with 9 diverse events |
| `test_db.py` | Test database connection with sample data |

## Pipeline Scripts (scripts_py/)

| Script | Description |
|--------|-------------|
| `embed_events.py` | Generate embeddings for events from `all_posts.json` |
| `populate_events.py` | Populate events table from JSON data |
| `send_newsletters.py` | Send personalized newsletters using Two-Tower recommender |
| `ingest_events.py` | Classify uncategorized events in batch |

## Project Structure

```
├── categorize_events.py    # Main: AI event categorization
├── generate_newsletter.py  # Main: Newsletter generation & sending
├── test_db.py              # Main: Database connection test
├── python_app/             # Core library modules
│   ├── config.py           # Configuration management
│   ├── embeddings.py       # OpenAI embeddings
│   ├── recommender.py      # Two-Tower recommendation engine
│   ├── scoring.py          # Event scoring logic
│   ├── vector_index.py     # Vector similarity search
│   ├── email_sender.py     # Email delivery service
│   ├── email_templates.py  # HTML email templates
│   ├── supabase_client.py  # Database client
│   └── openai_client.py    # OpenAI API client
├── scripts_py/             # Pipeline automation scripts
├── tests/                  # Unit tests for python_app
├── all_posts.json          # Event data source
└── requirements.txt        # Python dependencies
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
