# Connect3 Newsletter

[![Tests](https://github.com/Rudra-Tiwari-codes/Connect3-newsletter/actions/workflows/test.yml/badge.svg)](https://github.com/Rudra-Tiwari-codes/Connect3-newsletter/actions/workflows/test.yml)

A personalized event recommendation and newsletter system developed for DSCubed at the University of Melbourne.

**Authors:** Nirav and Rudra

## Overview

Connect3 delivers personalized university event newsletters using a two-phase recommendation approach. The system combines semantic embeddings with user interaction data to recommend relevant events based on individual preferences.

### Key Capabilities

- Event categorization using GPT-4o-mini
- Two-tower recommendation architecture with OpenAI embeddings
- Two-phase newsletter delivery (discovery followed by personalization)
- NumPy-accelerated vector search
- Personalized HTML newsletters with category-based event selection

## Technology Stack

| Component       | Technology                              |
|-----------------|----------------------------------------|
| Database        | Supabase (PostgreSQL)                  |
| Backend         | Python 3.12                            |
| Embeddings      | OpenAI text-embedding-3-small (1536d)  |
| Classification  | GPT-4o-mini                            |
| Email           | Gmail SMTP                             |
| Vector Search   | NumPy                                  |

## Requirements

- Python 3.12 or higher
- Supabase project with configured tables
- OpenAI API key
- Gmail account with App Password enabled

## Installation

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
```

Required variables:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `OPENAI_API_KEY`
- `GMAIL_USER`
- `GMAIL_APP_PASSWORD`

## Project Structure

```
connect3-newsletter/
├── python_app/                 # Core library modules
│   ├── config.py               # Configuration management
│   ├── embeddings.py           # OpenAI embedding generation
│   ├── recommender.py          # Two-tower recommendation engine
│   ├── vector_index.py         # Vector similarity search
│   ├── email_sender.py         # Email delivery service
│   ├── email_templates.py      # HTML email templates
│   ├── supabase_client.py      # Database client
│   └── openai_client.py        # OpenAI API client
├── scripts_py/                 # Pipeline scripts
│   ├── two_phase_newsletter.py # Main newsletter workflow
│   ├── embed_events.py         # Event embedding generation
│   ├── populate_events.py      # Database population
│   └── ingest_events.py        # Batch event classification
├── api/                        # Vercel serverless functions
│   ├── feedback.py             # Click tracking endpoint
│   ├── subscribe.py            # Subscription endpoint
│   └── unsubscribe.py          # Unsubscribe endpoint
├── tests/                      # Unit tests
├── database/                   # SQL migration scripts
├── categorize_events.py        # Event categorization script
├── all_posts.json              # Event data source
└── requirements.txt            # Python dependencies
```

## Two-Phase Newsletter System

The newsletter operates in two phases:

### Phase 1: Discovery
- Sends 9 randomly selected events to each subscriber
- User clicks indicate interest
- Interactions are recorded for preference learning

### Phase 2: Personalization
- Analyzes Phase 1 interaction data
- Distributes 9 events based on learned preferences:
  - 3 events from the user's top category
  - 3 events from the second category
  - 1 event from the third category
  - 2 events for exploration (random categories)

## Usage

### Generate Event Embeddings
```bash
python scripts_py/embed_events.py
```

### Categorize Events
```bash
python categorize_events.py
```

### Run Newsletter Pipeline
```bash
python scripts_py/two_phase_newsletter.py
```

### Run with Custom Delay
```python
from scripts_py.two_phase_newsletter import run_two_phase_newsletter
run_two_phase_newsletter(delay_minutes=1)
```

## Event Categories

The system classifies events into 13 categories:

| Category                    | Category                    |
|-----------------------------|-----------------------------|
| academic_workshops          | career_networking           |
| social_cultural             | sports_fitness              |
| arts_music                  | tech_innovation             |
| volunteering_community      | food_dining                 |
| travel_adventure            | health_wellness             |
| entrepreneurship            | environment_sustainability  |
| gaming_esports              |                             |

## Testing

Run the test suite:
```bash
pytest tests/ -v
```

## Database Setup

Execute the migration scripts in Supabase SQL Editor:
1. `database/migrate_tables.sql`
2. `database/migrate_to_pgvector.sql` (optional, for pgvector support)

## Deployment

The API endpoints are designed for deployment on Vercel as serverless functions. Configure the environment variables in the Vercel dashboard.

## License

MIT
