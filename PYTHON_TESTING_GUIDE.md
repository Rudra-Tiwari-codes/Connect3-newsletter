# Connect3 Python Workflow (Testing Guide)

This guide is the supplementary, hands-on workflow for running and validating the Python backend.

## 0) Setup (one-time)
1. Create/activate a virtualenv:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   ```
2. Install Python deps (covers `python_app` and the legacy FastAPI code):
   ```bash
   python -m pip install -r requirements.txt
   ```
3. Quick offline sanity check (no real API calls):
   ```bash
   PYTHONPATH=. pytest
   ```

## 1) Environment Variables
Create a local `.env` using `./.env.example` and set values:
- `OPENAI_API_KEY`
- `SUPABASE_URL` or `NEXT_PUBLIC_SUPABASE_URL`
- `SUPABASE_SERVICE_KEY` or `SUPABASE_SECRET_KEY`
- Optional: `OPENAI_TIMEOUT_SEC`, `OPENAI_MAX_RETRIES`
- For email: `GMAIL_USER`, `GMAIL_APP_PASSWORD`, optional `GMAIL_FROM_EMAIL`, `NEXT_PUBLIC_APP_URL`, `SMTP_TIMEOUT_SEC`

## 2) Supabase Setup
1. Create tables using:
   - `database/schema.sql`
   - `database/schema-embeddings.sql`
   - `database/seed.sql` (optional)
2. Use a service key for Python scripts.
3. Confirm the tables exist: `events`, `event_embeddings`, `users`, `user_preferences`, `feedback_logs`, `email_logs`.

## 3) Seed a Small Dataset
1. Ensure `all_posts.json` includes a few sample posts (id, caption, timestamp, permalink).
2. Insert test rows into `users` and `user_preferences`.

## 4) Run the Pipeline
1. Generate embeddings:
   - `PYTHONPATH=. python scripts_py/embed_events.py`
2. Classify uncategorized events:
   - `PYTHONPATH=. python scripts_py/ingest_events.py`
3. Rank and send newsletters (requires Gmail creds):
   - `PYTHONPATH=. python scripts_py/send_newsletters.py`
4. Optional recommender smoke test:
   ```bash
   PYTHONPATH=. python - <<'PY'
   from python_app.recommender import TwoTowerRecommender
   rec = TwoTowerRecommender()
   rec.load_event_index()
   print(rec.get_recommendations("YOUR_USER_ID"))
   PY
   ```

## 5) Verify Results
- `event_embeddings` has rows with embeddings/categories.
- `events.category` is populated for uncategorized rows.
- `email_logs` shows sent/failed entries after newsletter runs.
- The recommender returns a non-empty list when data exists.

If any step fails, re-check env vars, Supabase connectivity, and that your virtualenv has the dependencies from `requirements.txt`.
