"""Tests for python_app/pgvector_search.py vector search functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestSearchSimilarEvents:
    """Tests for search_similar_events function."""

    @patch("python_app.pgvector_search.USE_PGVECTOR", False)
    def test_returns_empty_when_disabled(self):
        """Returns empty list when pgvector is disabled."""
        from python_app.pgvector_search import search_similar_events
        
        result = search_similar_events([0.0] * 1536, top_k=10)
        assert result == []

    @patch("python_app.pgvector_search.USE_PGVECTOR", True)
    @patch("python_app.pgvector_search.supabase")
    def test_calls_match_events_rpc(self, mock_supabase):
        """Should call the match_events RPC function."""
        from python_app.pgvector_search import search_similar_events
        
        mock_response = Mock()
        mock_response.data = []
        mock_supabase.rpc.return_value.execute.return_value = mock_response
        
        query = [0.1] * 1536
        search_similar_events(query, top_k=5, threshold=0.7)
        
        mock_supabase.rpc.assert_called_once()
        call_args = mock_supabase.rpc.call_args
        assert call_args[0][0] == "match_events"

    @patch("python_app.pgvector_search.USE_PGVECTOR", True)
    @patch("python_app.pgvector_search.supabase")
    def test_returns_formatted_results(self, mock_supabase):
        """Should format results correctly."""
        from python_app.pgvector_search import search_similar_events
        
        mock_response = Mock()
        mock_response.data = [
            {"event_id": "evt1", "category": "tech", "similarity": 0.95},
            {"event_id": "evt2", "category": "sports", "similarity": 0.85},
        ]
        mock_supabase.rpc.return_value.execute.return_value = mock_response
        
        results = search_similar_events([0.1] * 1536, top_k=10)
        
        assert len(results) == 2
        assert results[0]["id"] == "evt1"
        assert results[0]["score"] == 0.95
        assert results[0]["category"] == "tech"

    @patch("python_app.pgvector_search.USE_PGVECTOR", True)
    @patch("python_app.pgvector_search.supabase")
    def test_excludes_specified_ids(self, mock_supabase):
        """Should exclude events with IDs in exclude_ids."""
        from python_app.pgvector_search import search_similar_events
        
        mock_response = Mock()
        mock_response.data = [
            {"event_id": "evt1", "similarity": 0.95},
            {"event_id": "evt2", "similarity": 0.85},
            {"event_id": "evt3", "similarity": 0.75},
        ]
        mock_supabase.rpc.return_value.execute.return_value = mock_response
        
        results = search_similar_events([0.1] * 1536, exclude_ids={"evt1", "evt3"})
        
        ids = [r["id"] for r in results]
        assert "evt1" not in ids
        assert "evt3" not in ids
        assert "evt2" in ids

    @patch("python_app.pgvector_search.USE_PGVECTOR", True)
    @patch("python_app.pgvector_search.supabase")
    def test_respects_top_k_limit(self, mock_supabase):
        """Should return at most top_k results."""
        from python_app.pgvector_search import search_similar_events
        
        mock_response = Mock()
        mock_response.data = [{"event_id": f"evt{i}", "similarity": 0.9-i*0.1} for i in range(10)]
        mock_supabase.rpc.return_value.execute.return_value = mock_response
        
        results = search_similar_events([0.1] * 1536, top_k=3)
        
        assert len(results) <= 3

    @patch("python_app.pgvector_search.USE_PGVECTOR", True)
    @patch("python_app.pgvector_search.supabase")
    def test_handles_empty_response(self, mock_supabase):
        """Should handle empty response gracefully."""
        from python_app.pgvector_search import search_similar_events
        
        mock_response = Mock()
        mock_response.data = None
        mock_supabase.rpc.return_value.execute.return_value = mock_response
        
        results = search_similar_events([0.1] * 1536)
        assert results == []

    @patch("python_app.pgvector_search.USE_PGVECTOR", True)
    @patch("python_app.pgvector_search.supabase")
    def test_handles_rpc_exception(self, mock_supabase):
        """Should return empty list on RPC exception."""
        from python_app.pgvector_search import search_similar_events
        
        mock_supabase.rpc.return_value.execute.side_effect = Exception("RPC error")
        
        results = search_similar_events([0.1] * 1536)
        assert results == []


class TestUpsertEmbeddingPgvector:
    """Tests for upsert_embedding_pgvector function."""

    @patch("python_app.pgvector_search.USE_PGVECTOR", False)
    def test_returns_false_when_disabled(self):
        """Returns False when pgvector is disabled."""
        from python_app.pgvector_search import upsert_embedding_pgvector
        
        result = upsert_embedding_pgvector("evt1", [0.0] * 1536)
        assert result is False

    @patch("python_app.pgvector_search.USE_PGVECTOR", True)
    @patch("python_app.pgvector_search.supabase")
    def test_upserts_to_table(self, mock_supabase):
        """Should upsert to the pgvector table."""
        from python_app.pgvector_search import upsert_embedding_pgvector
        
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = Mock()
        
        result = upsert_embedding_pgvector("evt1", [0.5] * 1536, category="tech")
        
        assert result is True
        mock_supabase.table.assert_called()

    @patch("python_app.pgvector_search.USE_PGVECTOR", True)
    @patch("python_app.pgvector_search.supabase")
    def test_returns_false_on_exception(self, mock_supabase):
        """Should return False on exception."""
        from python_app.pgvector_search import upsert_embedding_pgvector
        
        mock_supabase.table.return_value.upsert.side_effect = Exception("DB error")
        
        result = upsert_embedding_pgvector("evt1", [0.5] * 1536)
        assert result is False


class TestIsPgvectorAvailable:
    """Tests for is_pgvector_available function."""

    @patch("python_app.pgvector_search.USE_PGVECTOR", False)
    def test_returns_false_when_disabled(self):
        """Returns False when USE_PGVECTOR is False."""
        from python_app.pgvector_search import is_pgvector_available
        
        assert is_pgvector_available() is False

    @patch("python_app.pgvector_search.USE_PGVECTOR", True)
    @patch("python_app.pgvector_search.supabase")
    def test_returns_true_when_rpc_succeeds(self, mock_supabase):
        """Returns True when match_events RPC succeeds."""
        from python_app.pgvector_search import is_pgvector_available
        
        mock_supabase.rpc.return_value.execute.return_value = Mock()
        
        assert is_pgvector_available() is True

    @patch("python_app.pgvector_search.USE_PGVECTOR", True)
    @patch("python_app.pgvector_search.supabase")
    def test_returns_false_on_exception(self, mock_supabase):
        """Returns False when RPC fails."""
        from python_app.pgvector_search import is_pgvector_available
        
        mock_supabase.rpc.return_value.execute.side_effect = Exception("Not available")
        
        assert is_pgvector_available() is False
