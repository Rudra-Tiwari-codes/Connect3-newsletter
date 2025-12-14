import importlib
from datetime import datetime, timedelta, timezone


class _FakeQuery:
  def __init__(self, data):
    self.data = data

  # Chainable methods
  def select(self, *args, **kwargs):
    return self

  def eq(self, *args, **kwargs):
    return self

  def gte(self, *args, **kwargs):
    return self

  def order(self, *args, **kwargs):
    return self

  def limit(self, *args, **kwargs):
    return self

  def execute(self):
    return self


class _FakeSupabase:
  def __init__(self, users, prefs, events):
    self._users = users
    self._prefs = prefs
    self._events = events

  def table(self, name):
    if name == "users":
      return _FakeQuery(self._users)
    if name == "user_preferences":
      return _FakeQuery(self._prefs)
    if name == "events":
      return _FakeQuery(self._events)
    return _FakeQuery([])


def test_rank_events_for_user_prioritizes_preference_and_urgency(monkeypatch):
  # Dummy env to satisfy supabase client on import
  monkeypatch.setenv("SUPABASE_URL", "http://localhost")
  monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
  import python_app.scoring as scoring
  importlib.reload(scoring)

  now = datetime.now(timezone.utc)
  events = [
    {
      "id": "near-pref",
      "category": "tech_innovation",
      "event_date": (now + timedelta(days=1)).isoformat(),
    },
    {
      "id": "far-pref",
      "category": "tech_innovation",
      "event_date": (now + timedelta(days=25)).isoformat(),
    },
    {
      "id": "near-nopref",
      "category": "sports_fitness",
      "event_date": (now + timedelta(days=1)).isoformat(),
    },
  ]
  fake = _FakeSupabase(
    users=[{"id": "u1"}],
    prefs=[{"user_id": "u1", "tech_innovation": 1.0, "sports_fitness": 0.1}],
    events=events,
  )

  monkeypatch.setattr(scoring, "supabase", fake)

  ranked = scoring.rank_events_for_user("u1", limit=3)
  ids = [e["id"] for e in ranked]

  # Preference + urgency should put "near-pref" first
  assert ids[0] == "near-pref"
  # "far-pref" should rank above "near-nopref" due to strong preference weight
  assert ids.index("far-pref") < ids.index("near-nopref")
