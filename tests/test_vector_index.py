from python_app.vector_index import VectorIndex


def test_vector_index_search_orders_by_similarity():
  index = VectorIndex(dimension=3)
  index.add("a", [1.0, 0.0, 0.0])
  index.add("b", [0.0, 1.0, 0.0])
  index.add("c", [0.5, 0.5, 0.0])

  results = index.search([1.0, 0.0, 0.0], top_k=2)
  ids = [r["id"] for r in results]

  assert ids[0] == "a"
  # "c" should be closer to "a" than "b"
  assert "c" in ids
