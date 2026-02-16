"""Comprehensive tests for python_app/vector_index.py."""

import pytest
import numpy as np
from python_app.vector_index import VectorIndex


class TestVectorIndexBasics:
    """Basic functionality tests for VectorIndex."""

    def test_add_and_size(self):
        """Can add vectors and track size."""
        index = VectorIndex(dimension=3)
        assert index.size() == 0
        
        index.add("a", [1.0, 0.0, 0.0])
        assert index.size() == 1
        
        index.add("b", [0.0, 1.0, 0.0])
        assert index.size() == 2

    def test_add_with_metadata(self):
        """Can store and retrieve metadata."""
        index = VectorIndex(dimension=3)
        index.add("a", [1.0, 0.0, 0.0], {"category": "test"})
        
        results = index.search([1.0, 0.0, 0.0], top_k=1)
        assert results[0]["metadata"]["category"] == "test"

    def test_update_existing_vector(self):
        """Re-adding same ID updates the vector."""
        index = VectorIndex(dimension=3)
        index.add("a", [1.0, 0.0, 0.0])
        index.add("a", [0.0, 1.0, 0.0])  # Update
        
        assert index.size() == 1  # Still 1, not 2
        
        # Search should find the updated vector
        results = index.search([0.0, 1.0, 0.0], top_k=1)
        assert results[0]["id"] == "a"
        assert results[0]["score"] > 0.99  # Perfect match

    def test_remove_vector(self):
        """Can remove vectors by ID."""
        index = VectorIndex(dimension=3)
        index.add("a", [1.0, 0.0, 0.0])
        index.add("b", [0.0, 1.0, 0.0])
        
        index.remove("a")
        assert index.size() == 1
        
        results = index.search([1.0, 0.0, 0.0], top_k=1)
        assert results[0]["id"] == "b"  # Only b remains

    def test_clear(self):
        """Can clear all vectors."""
        index = VectorIndex(dimension=3)
        index.add("a", [1.0, 0.0, 0.0])
        index.add("b", [0.0, 1.0, 0.0])
        
        index.clear()
        assert index.size() == 0

    def test_dimension_mismatch_raises(self):
        """Wrong dimension raises ValueError."""
        index = VectorIndex(dimension=3)
        
        with pytest.raises(ValueError, match="Expected dimension"):
            index.add("a", [1.0, 0.0])  # Only 2 dims


class TestVectorIndexSearch:
    """Search functionality tests."""

    def test_search_orders_by_similarity(self):
        """Results are ordered by similarity descending."""
        index = VectorIndex(dimension=3)
        index.add("a", [1.0, 0.0, 0.0])
        index.add("b", [0.0, 1.0, 0.0])
        index.add("c", [0.5, 0.5, 0.0])
        
        results = index.search([1.0, 0.0, 0.0], top_k=3)
        ids = [r["id"] for r in results]
        
        assert ids[0] == "a"  # Exact match first
        assert ids[1] == "c"  # Partial match second
        assert ids[2] == "b"  # Orthogonal last

    def test_search_top_k_limit(self):
        """Returns at most top_k results."""
        index = VectorIndex(dimension=3)
        for i in range(10):
            index.add(f"v{i}", [float(i), 0.0, 0.0])
        
        results = index.search([5.0, 0.0, 0.0], top_k=3)
        assert len(results) == 3

    def test_search_exclude_ids(self):
        """Can exclude specific IDs from results."""
        index = VectorIndex(dimension=3)
        index.add("a", [1.0, 0.0, 0.0])
        index.add("b", [0.9, 0.1, 0.0])
        index.add("c", [0.0, 1.0, 0.0])
        
        results = index.search([1.0, 0.0, 0.0], top_k=2, exclude_ids={"a"})
        ids = [r["id"] for r in results]
        
        assert "a" not in ids
        assert "b" in ids

    def test_search_empty_index(self):
        """Returns empty list when index is empty."""
        index = VectorIndex(dimension=3)
        results = index.search([1.0, 0.0, 0.0], top_k=5)
        assert results == []

    def test_search_zero_query_vector(self):
        """Zero query vector returns empty results."""
        index = VectorIndex(dimension=3)
        index.add("a", [1.0, 0.0, 0.0])
        
        results = index.search([0.0, 0.0, 0.0], top_k=5)
        assert results == []


class TestVectorIndexBatch:
    """Batch operation tests."""

    def test_add_batch(self):
        """Can add multiple vectors in batch."""
        index = VectorIndex(dimension=3)
        entries = [
            {"id": "a", "vector": [1.0, 0.0, 0.0], "metadata": {"cat": "x"}},
            {"id": "b", "vector": [0.0, 1.0, 0.0], "metadata": {"cat": "y"}},
            {"id": "c", "vector": [0.0, 0.0, 1.0], "metadata": {"cat": "z"}},
        ]
        
        index.add_batch(entries)
        assert index.size() == 3

    def test_add_batch_empty(self):
        """Empty batch does nothing."""
        index = VectorIndex(dimension=3)
        index.add_batch([])
        assert index.size() == 0


class TestVectorIndexFilter:
    """Filtered search tests."""

    def test_search_with_filter(self):
        """Can filter by metadata predicate."""
        index = VectorIndex(dimension=3)
        index.add("a", [1.0, 0.0, 0.0], {"active": True})
        index.add("b", [0.9, 0.1, 0.0], {"active": False})
        index.add("c", [0.8, 0.2, 0.0], {"active": True})
        
        results = index.search_with_filter(
            [1.0, 0.0, 0.0],
            top_k=3,
            predicate=lambda m: m and m.get("active") is True
        )
        ids = [r["id"] for r in results]
        
        assert "b" not in ids
        assert "a" in ids
        assert "c" in ids
