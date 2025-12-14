import importlib


class _FakeQuery:
  def __init__(self, data):
    self.data = data

  def select(self, *args, **kwargs):
    return self

  def eq(self, *args, **kwargs):
    return self

  def in_(self, *args, **kwargs):
    return self

  def limit(self, *args, **kwargs):
    return self

  def execute(self):
    return self


class _FakeSupabase:
  def __init__(self, feedback, embeddings, prefs):
    self._feedback = feedback
    self._embeddings = embeddings
    self._prefs = prefs

  def table(self, name):
    if name == "feedback_logs":
      return _FakeQuery(self._feedback)
    if name == "event_embeddings":
      return _FakeQuery(self._embeddings)
    if name == "user_preferences":
      return _FakeQuery(self._prefs)
    return _FakeQuery([])


def test_embed_user_uses_weighted_history(monkeypatch):
  monkeypatch.setenv("OPENAI_API_KEY", "test-key")
  monkeypatch.setenv("SUPABASE_URL", "http://localhost")
  monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
  import python_app.embeddings as emb
  importlib.reload(emb)
  # Prevent real OpenAI calls
  monkeypatch.setattr(emb, "generate_embedding", lambda text: [1.0, 1.0, 1.0])
  monkeypatch.setattr(emb, "EMBEDDING_DIM", 3)

  feedback = [{"event_id": "e1", "action": "like"}, {"event_id": "e2", "action": "dislike"}]
  embeddings = [
    {"event_id": "e1", "embedding": [1.0, 0.0, 0.0]},
    {"event_id": "e2", "embedding": [0.0, 1.0, 0.0]},
  ]
  prefs = []
  fake = _FakeSupabase(feedback, embeddings, prefs)
  monkeypatch.setattr(emb, "supabase", fake)

  vec = emb.embed_user("user-1")
  # like is +1, dislike is -0.5 => resulting vector should lean positive on first dimension
  assert vec[0] > vec[1]
