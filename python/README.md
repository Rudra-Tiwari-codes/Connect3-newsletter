# Connect3 Python Backend

Python implementation of the Connect3 Two-Tower Email Recommendation System.

## Setup

1. Create virtual environment:
```bash
cd python
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure `.env` file is configured in the parent directory with:
```
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_service_key
OPENAI_API_KEY=your_openai_key
```

## Running the API

```bash
# From the project root
uvicorn python.main:app --reload --port 8000
```

Visit http://localhost:8000/docs for API documentation.

## Running Scripts

```bash
# Generate students
python -m python.scripts.generate_students

# Run clustering
python -m python.scripts.update_clusters

# Generate recommendations
python -m python.scripts.run_recommendations

# Run local demo (no database)
python -m python.scripts.demo_local
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/api/recommendations/{user_id}` | GET | Get recommendations |
| `/api/feedback` | POST | Submit feedback |
| `/api/events` | GET | List events |
| `/api/users` | GET | List users |
| `/api/cluster` | POST | Trigger clustering |

## Project Structure

```
python/
├── main.py                 # FastAPI entry point
├── requirements.txt        # Dependencies
├── lib/                    # Core library modules
│   ├── config.py          # Configuration
│   ├── supabase_client.py # Database client
│   ├── embeddings.py      # OpenAI embeddings
│   ├── vector_index.py    # Vector search
│   ├── recommender.py     # Two-tower recommender
│   ├── scoring.py         # Event scoring
│   ├── clustering.py      # PCA clustering
│   ├── email_delivery.py  # Email sending
│   └── email_template.py  # HTML templates
└── scripts/               # CLI scripts
    ├── generate_students.py
    ├── update_clusters.py
    ├── run_recommendations.py
    └── demo_local.py
```
