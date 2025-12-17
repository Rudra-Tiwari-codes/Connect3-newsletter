# Connect3 Python Backend Review (Primary Technical Spec)

This document is the primary technical specification for the Python backend.
For execution and verification steps, see `PYTHON_TESTING_GUIDE.md`.

## 1) Repository Walkthrough (Python)

#### File: python_app/config.py
- Responsibility: Env loading helpers; optionally loads `.env`.
- Inputs: OS environment.
- Outputs: `require_env`, `get_env` values.
- External dependencies: `dotenv` (optional).
- Called by: supabase client, embeddings, email, scripts.
- Risk level: Low (missing vars raise early; `.env.example` guides setup).

#### File: python_app/openai_client.py
- Responsibility: Shared OpenAI client configuration with retries/timeouts.
- Inputs: `OPENAI_API_KEY`, optional `OPENAI_TIMEOUT_SEC`, `OPENAI_MAX_RETRIES`.
- Outputs: `client`, `with_retry` helper.
- External dependencies: OpenAI API.
- Called by: embeddings, ai_classifier.
- Risk level: Low (timeouts/retries reduce transient failure risk).

#### File: python_app/supabase_client.py
- Responsibility: Build Supabase client with service key.
- Inputs: `SUPABASE_URL`/`NEXT_PUBLIC_SUPABASE_URL`, `SUPABASE_SERVICE_KEY`/`SUPABASE_SECRET_KEY`.
- Outputs: `supabase: Client`.
- External dependencies: `supabase` Python SDK; network access to Supabase DB.
- Called by: embeddings, scoring, email_sender, recommender, scripts.
- Risk level: Medium (service key still required; `ensure_ok` surfaces errors early).

#### File: python_app/embeddings.py
- Responsibility: Generate OpenAI embeddings; classify category; build user embedding.
- Inputs: OpenAI API key, event captions, user_id (for history/preferences).
- Outputs: `generate_embedding`, `classify_event_category`, `embed_event`, `embed_user`, constants.
- External dependencies: OpenAI API, Supabase tables `feedback_logs`, `event_embeddings`, `user_preferences`.
- Called by: scripts_py/embed_events.py, scoring/recommender indirectly via user embeddings.
- Risk level: Medium (timeouts/retries + embedding shape checks).

#### File: python_app/ai_classifier.py
- Responsibility: Classify events into enumerated categories via OpenAI Chat.
- Inputs: Event dict (id/title/description/location).
- Outputs: `EventClassifier.classify_event`, `classify_batch`; category string.
- External dependencies: OpenAI API.
- Called by: scripts_py/ingest_events.py.
- Risk level: Medium (retries/timeouts; still cost and default fallback).

#### File: python_app/vector_index.py
- Responsibility: In-memory cosine similarity index.
- Inputs: Vectors with IDs.
- Outputs: `search`, `search_with_filter`, CRUD ops.
- External dependencies: None.
- Called by: recommender.
- Risk level: Low (no persistence; assumes correct dimension).

#### File: python_app/scoring.py
- Responsibility: Score/rank events using preference weight and urgency.
- Inputs: user_id; reads `users`, `user_preferences`, `events`.
- Outputs: Ranked list with scores; `EventScoringService` wrapper.
- External dependencies: Supabase.
- Called by: scripts_py/send_newsletters.py.
- Risk level: Low (explicit errors on missing user/prefs; Supabase errors surfaced).

#### File: python_app/email_templates.py
- Responsibility: Build HTML for personalized newsletter cards.
- Inputs: user dict, events list, feedback base URL.
- Outputs: HTML string.
- External dependencies: None.
- Called by: email_sender, tests.
- Risk level: Low (string-only).

#### File: python_app/email_sender.py
- Responsibility: Send emails via Gmail SMTP; log results.
- Inputs: Gmail creds, user_id/events, Supabase client.
- Outputs: Sends email; writes `email_logs`; `EmailDeliveryService`.
- External dependencies: SMTP over network, Supabase.
- Called by: scripts_py/send_newsletters.py.
- Risk level: Medium (SMTP timeout, log error handling).

#### File: python_app/recommender.py
- Responsibility: Two-tower recommender (load embeddings, compute recs, apply business rules).
- Inputs: user_id(s); reads `event_embeddings`, `feedback_logs`, `events`.
- Outputs: Ranked recommendations with reason text.
- External dependencies: Supabase, in-memory VectorIndex, embeddings.embed_user, OpenAI via embed_user.
- Called by: (not yet wired into scripts), candidate for pipeline.
- Risk level: Medium (Supabase errors surfaced; embedding dimension validation).

#### File: python_app/__init__.py
- Responsibility: Package marker.
- Inputs/Outputs: None.
- External dependencies: None.
- Called by: imports.
- Risk level: Low.

#### File: scripts_py/embed_events.py
- Responsibility: Read `all_posts.json`, embed & classify events, upsert embeddings.
- Inputs: Local JSON file; OpenAI API; Supabase `event_embeddings`.
- Outputs: Upserted rows; console logs.
- External dependencies: OpenAI, Supabase.
- Called by: manual CLI.
- Risk level: Medium (Supabase errors surfaced; retries/timeouts on OpenAI).

#### File: scripts_py/ingest_events.py
- Responsibility: Classify uncategorized events in `events` table.
- Inputs: Supabase `events`; OpenAI via `EventClassifier`.
- Outputs: Updates `events.category`.
- External dependencies: OpenAI, Supabase.
- Called by: manual CLI.
- Risk level: Medium (retries/timeouts; default fallback remains).

#### File: scripts_py/send_newsletters.py
- Responsibility: Rank events per user and send newsletters.
- Inputs: Supabase `users`, `events`, `user_preferences`; Gmail SMTP.
- Outputs: Emails sent; `email_logs` writes.
- External dependencies: Supabase, SMTP.
- Called by: manual CLI.
- Risk level: Medium (Supabase errors surfaced; SMTP timeout).

#### Tests (tests/*.py)
- Responsibility: Unit coverage for vector index, scoring, embeddings, email templates.
- Inputs: Fake data, monkeypatched env.
- Outputs: Verifies ordering and template content.
- External dependencies: None (uses monkeypatch to avoid network).
- Called by: pytest.
- Risk level: Low.

## 2) System Architecture (End-to-End)
- Data origin: Instagram-like posts in `all_posts.json`; users & prefs/events stored in Supabase.
- Embedding flow: `scripts_py/embed_events.py` → OpenAI embedding/classification → Supabase `event_embeddings` (no event upsert).
- Classification flow: `scripts_py/ingest_events.py` → OpenAI classifier → update `events.category`.
- Recommendation flow: `python_app/recommender.py` (load embeddings → embed user via history/prefs → vector search → recency/diversity rerank → reasons).
- Scoring flow (emails): `python_app/scoring.py` ranks events by preference weight + urgency.
- Email flow: `scripts_py/send_newsletters.py` → scoring → `EmailDeliveryService` → Gmail SMTP → log to `email_logs`.
- Scheduling: None present; all scripts are manual CLI entrypoints.

ASCII Flow:
```
all_posts.json --> embed_events.py --OpenAI--> embeddings -> supabase.event_embeddings
supabase.events (uncategorized) --> ingest_events.py --OpenAI--> update events.category
users/prefs + events --> scoring.py --> ranked events
feedback_logs + event_embeddings --> recommender.py (embed_user + vector search) --> recommendations
ranked events per user --> send_newsletters.py --> email_sender.py --SMTP--> recipients, logs to email_logs
feedback URLs (Next.js API) --> feedback_logs/preferences updates (TS path, not Python)
```

## 3) Supabase Integration
- Tables read: `events`, `event_embeddings`, `users`, `user_preferences`, `feedback_logs`, `email_logs`.
- Tables written:
  - `event_embeddings` (embed_events.py)
  - `events.category` (ingest_events.py)
  - `email_logs` (email_sender.py success/failure)
  - Reads `feedback_logs` for user embedding; writes not performed in Python (feedback handled in TS API).
- Credentials: Uses service key (from SUPABASE_SERVICE_KEY/SECRET_KEY) everywhere. Assumes full RLS bypass.
- RLS implications: Service key ignores RLS; if mis-set to anon, most writes/read will fail. If RLS enabled without policies and service key not used, ingestion/email fail explicitly via `ensure_ok`.
- Breakage: Missing URL/key → RuntimeError on import. Wrong key (anon) → select/insert failures, surfaced early.
- Dangerous usage: Service key in long-lived scripts; mitigate by keeping `.env` local, using `.env.example`, and rotating keys regularly.

## 4) Security & Failure Analysis
- High: Service key used in scripts; risk of leakage if logs/CI capture env. Consequence: full DB compromise. Mitigation: keep `.env` local, use secrets manager, rotate keys.
- Medium: OpenAI calls can still fail or rate limit; retries/timeouts reduce but do not eliminate.
- Medium: Email sender depends on Gmail creds; SMTP timeout avoids hangs but no retry/backoff for delivery.
- Medium: `embed_user` and recommender assume correct embedding dimensions; now validated, but malformed DB rows are skipped (reducing recall).
- Medium: Ingestion/classification default category fallback may pollute `events.category` with generic class; no confidence threshold.
- Medium: Batch scripts have minimal rate limiting (1s per 5 events); could hit OpenAI/Supabase rate limits without backoff.
- Medium: No idempotency markers; re-running embed_events will upsert embeddings but not events table (by design); send_newsletters may resend without guard.
- Medium: No input validation on `all_posts.json` content; malformed timestamps now yield 0 urgency (events may rank lower).
- Low: Email HTML uses inline feedback links without signing parameters; could be abused if link leaked (mitigated by TS feedback API UUID validation).

## 5) Testing and Workflow
See `PYTHON_TESTING_GUIDE.md` for step-by-step setup and verification.
