# CONNECCT Project Issues & Loopholes

> Analysis conducted on 2026-01-04

---

## 🔴 Critical Issues

### 1. In-Memory Rate Limiting Doesn't Work in Serverless

**File:** [`api/feedback.py`](file:///c:/Users/tiwar/OneDrive%20-%20The%20University%20of%20Melbourne/Desktop/CONNECCT/api/feedback.py) (lines 74-105)

**Problem:** Rate limiting uses an in-memory dictionary `_rate_limit_store` that resets on every cold start. In Vercel serverless, each request can hit a new instance, making this **completely ineffective**.

```python
# Current implementation - resets on cold start
_rate_limit_store: dict = defaultdict(list)
_rate_limit_lock = Lock()
```

**Fix:** Use Redis, Upstash, or database-backed rate limiting.

---

### 2. Unsubscribe Token Secret Not Required

**File:** [`api/unsubscribe.py`](file:///c:/Users/tiwar/OneDrive%20-%20The%20University%20of%20Melbourne/Desktop/CONNECCT/api/unsubscribe.py) (lines 62-65)

**Problem:** If `UNSUBSCRIBE_TOKEN_SECRET` is not set, the token validation is **skipped entirely**. Anyone can unsubscribe any user by knowing/guessing their `uid`.

```python
if UNSUBSCRIBE_TOKEN_SECRET:
    if not _is_valid_token(user_id, token, UNSUBSCRIBE_TOKEN_SECRET):
        _send_plain(self, 403, "Invalid or missing token.")
        return
```

**Fix:** Make the token validation mandatory or add alternative authentication.

---

## 🟠 Security Concerns

### 3. Overly Permissive RLS Policies

**File:** [`database/migrate_tables.sql`](file:///c:/Users/tiwar/OneDrive%20-%20The%20University%20of%20Melbourne/Desktop/CONNECCT/database/migrate_tables.sql) (lines 40-41, 75-76, 98-99)

**Problem:** Policies like `"Allow all event_embeddings" FOR ALL USING (true)` effectively disable row-level security. Anyone with the anon key can modify data.

```sql
CREATE POLICY "Allow all event_embeddings" ON public.event_embeddings
    FOR ALL USING (true) WITH CHECK (true);
```

**Fix:** Use proper role-based policies restricting write access to service role only.

---

### 4. Error Message Information Leak

**File:** [`api/unsubscribe.py`](file:///c:/Users/tiwar/OneDrive%20-%20The%20University%20of%20Melbourne/Desktop/CONNECCT/api/unsubscribe.py) (line 78)

**Problem:** Internal error details are exposed to users:

```python
_send_plain(self, 500, f"Failed to unsubscribe: {exc}")
```

**Fix:** Log the full error internally, but return a generic message to users.

---

## 🟡 Code Quality Issues

### 5. Incomplete `requirements.txt`

**File:** [`requirements.txt`](file:///c:/Users/tiwar/OneDrive%20-%20The%20University%20of%20Melbourne/Desktop/CONNECCT/requirements.txt)

**Current content:**
```
supabase
python-dotenv
openai
numpy
jinja2
requests
```

**Problems:**
- No version pinning (can cause reproducibility issues)
- Missing `pytest` for running tests
- No development dependencies separated

**Fix:** Pin versions and consider using `requirements-dev.txt` for test dependencies.

---

### 6. Print Statement in Production Code

**File:** [`python_app/email_sender.py`](file:///c:/Users/tiwar/OneDrive%20-%20The%20University%20of%20Melbourne/Desktop/CONNECCT/python_app/email_sender.py) (line 69)

**Problem:** Uses `print()` instead of logger:

```python
print(f"Skipping unsubscribed user: {user_email}")
```

**Fix:** Use `logger.info()` for consistency.

---

### 7. Hardcoded Production URLs

**Files:**
- [`email_sender.py`](file:///c:/Users/tiwar/OneDrive%20-%20The%20University%20of%20Melbourne/Desktop/CONNECCT/python_app/email_sender.py) (line 20)
- [`api/feedback.py`](file:///c:/Users/tiwar/OneDrive%20-%20The%20University%20of%20Melbourne/Desktop/CONNECCT/api/feedback.py) (lines 332, 350)

**Problem:** URLs are hardcoded:

```python
FEEDBACK_URL = "https://connect3-newsletter.vercel.app/feedback"
self.send_redirect('https://connect3.app')
```

**Fix:** Use environment variables for configurability across environments.

---

## 🟢 Architectural Concerns

### 8. Silent Exception Swallowing

**File:** [`python_app/scoring.py`](file:///c:/Users/tiwar/OneDrive%20-%20The%20University%20of%20Melbourne/Desktop/CONNECCT/python_app/scoring.py) (lines 91-92)

**Problem:** Silently catches and ignores datetime parsing errors:

```python
try:
    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
    # ...
except Exception:
    pass  # Silent failure
```

**Fix:** Log warnings for debugging purposes.

---

### 9. No Retry Logic for External API Calls

**Files:** `email_sender.py`, `openai_client.py`

**Problem:** Single SMTP/OpenAI calls without retry logic can fail on transient errors.

**Fix:** Implement exponential backoff retry logic.

---

### 10. Test Coverage Gaps

**Current tests:**
- `test_scoring.py`
- `test_embeddings.py`
- `test_email_templates.py`
- `test_vector_index.py`

**Missing coverage:**
- `api/feedback.py` - No tests
- `api/unsubscribe.py` - No tests
- `python_app/recommender.py` - No tests
- Database integration tests - None

---

## 💡 Minor Improvements

| Issue | File | Suggestion |
|-------|------|------------|
| Magic numbers | `scoring.py` | Move `CLUSTER_MATCH_WEIGHT=50`, `MAX_URGENCY_SCORE=30` to config |
| No type hints in tests | `tests/*.py` | Add type hints for better IDE support |
| Duplicate Supabase client init | `api/feedback.py` vs `python_app/supabase_client.py` | Consolidate to single import |
| Inconsistent error handling | Multiple files | Standardize error response format |

---

## Priority Recommendations

1. **Immediate:** Fix unsubscribe token validation (security critical)
2. **High:** Replace in-memory rate limiting with persistent solution
3. **Medium:** Tighten RLS policies on database tables
4. **Low:** Code quality improvements and test coverage

---

*This analysis was generated by reviewing the codebase structure, security patterns, and best practices.*
