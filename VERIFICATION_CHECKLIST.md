# Connect3 Codebase Verification Checklist

Step-by-step guide to verify the entire Python codebase is working correctly.

## Prerequisites

- [ ] Python 3.8+ installed
- [ ] `.env` file with `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `OPENAI_API_KEY`
- [ ] Dependencies installed: `pip install -r requirements.txt` (or `npm install` for Node dependencies)

---

## Step 1: Verify Python Imports

Run each command to verify all modules import correctly:

```bash
# Core config (no external dependencies)
python -c "from python.lib import config; print('✓ config.py')"

# Vector index (no external dependencies)
python -c "from python.lib import vector_index; print('✓ vector_index.py')"

# Supabase client (requires .env)
python -c "from python.lib import supabase_client; print('✓ supabase_client.py')"

# Email template (requires jinja2)
python -c "from python.lib import email_template; print('✓ email_template.py')"

# Embeddings (requires openai, .env)
python -c "from python.lib import embeddings; print('✓ embeddings.py')"

# Scoring
python -c "from python.lib import scoring; print('✓ scoring.py')"

# Clustering (requires numpy, sklearn)
python -c "from python.lib import clustering; print('✓ clustering.py')"

# Recommender
python -c "from python.lib import recommender; print('✓ recommender.py')"

# Email delivery
python -c "from python.lib import email_delivery; print('✓ email_delivery.py')"
```

---

## Step 2: Verify FastAPI Server

```bash
# Start the server
uvicorn python.main:app --port 8000

# In another terminal, test endpoints:
curl http://localhost:8000/
curl http://localhost:8000/api/health
```

Expected: `{"status":"ok","service":"Connect3 Recommendation API","version":"2.0.0"}`

---

## Step 3: Run Demo Script (No Database)

```bash
python -m python.scripts.demo_local
```

Expected: Shows mock recommendations for Alice, Bob, and Charlie.

---

## Step 4: Verify Database Connection

```bash
# Test Supabase connectivity
python -c "from python.lib.supabase_client import supabase; print(supabase.table('users').select('id').limit(1).execute())"
```

---

## Step 5: Run Clustering (Requires Users in DB)

```bash
python -m python.scripts.update_clusters
```

Expected: "Successfully clustered X users into Y clusters"

---

## Step 6: Run Recommendations (Requires Events + Users)

```bash
# Dry run (no emails)
python -m python.scripts.run_recommendations --limit 5

# With emails (requires GMAIL_USER and GMAIL_APP_PASSWORD)
# python -m python.scripts.run_recommendations --limit 5 --send
```

---

## Quick All-in-One Test

Run this single command to test all imports at once:

```bash
python -c "
from python.lib import config
from python.lib import vector_index
from python.lib import supabase_client
from python.lib import email_template
from python.lib import embeddings
from python.lib import scoring
from python.lib import clustering
from python.lib import recommender
from python.lib import email_delivery
from python import main
print('✅ All Python modules imported successfully!')
"
```

---

## Common Issues

| Error | Solution |
|-------|----------|
| `Missing Supabase environment variables` | Add `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` to `.env` |
| `Missing OpenAI API key` | Add `OPENAI_API_KEY` to `.env` |
| `ModuleNotFoundError: No module named 'supabase'` | Run `pip install supabase` |
| `ModuleNotFoundError: No module named 'sklearn'` | Run `pip install scikit-learn` |
| `ModuleNotFoundError: No module named 'jinja2'` | Run `pip install jinja2` |

---

## File Structure Reference

```
python/
├── __init__.py
├── main.py                    # FastAPI app entry point
├── api/
│   └── __init__.py
├── lib/
│   ├── __init__.py
│   ├── config.py              # Configuration constants
│   ├── supabase_client.py     # Database client
│   ├── embeddings.py          # Two-tower embedding service
│   ├── vector_index.py        # In-memory vector index
│   ├── scoring.py             # Event scoring service
│   ├── clustering.py          # User clustering (PCA + K-means)
│   ├── recommender.py         # Main recommendation engine
│   ├── email_template.py      # HTML email templates
│   └── email_delivery.py      # SMTP email sender
└── scripts/
    ├── __init__.py
    ├── demo_local.py          # Local demo (no DB)
    ├── generate_students.py   # Create test users
    ├── run_recommendations.py # Generate recommendations
    └── update_clusters.py     # Re-cluster users
```
