"""Tests for python_app/categories.py category definitions."""

import pytest


class TestCategoryConstants:
    """Tests for category constant definitions."""

    def test_has_14_categories(self):
        """Should have exactly 14 categories."""
        from python_app.categories import CONNECT3_CATEGORIES, NUM_CATEGORIES
        
        assert len(CONNECT3_CATEGORIES) == 14
        assert NUM_CATEGORIES == 14

    def test_categories_are_lowercase_underscore(self):
        """All categories should be lowercase with underscores."""
        from python_app.categories import CONNECT3_CATEGORIES
        
        for cat in CONNECT3_CATEGORIES:
            assert cat.islower(), f"Category {cat} is not lowercase"
            assert " " not in cat, f"Category {cat} contains spaces"
            assert "-" not in cat, f"Category {cat} contains dashes"

    def test_categories_list_matches_set(self):
        """List and set should contain same categories."""
        from python_app.categories import CONNECT3_CATEGORIES, CONNECT3_CATEGORIES_SET
        
        assert set(CONNECT3_CATEGORIES) == CONNECT3_CATEGORIES_SET

    def test_uniform_baseline_calculation(self):
        """Uniform baseline should be 1/NUM_CATEGORIES."""
        from python_app.categories import NUM_CATEGORIES, UNIFORM_BASELINE
        
        expected = 1.0 / NUM_CATEGORIES
        assert UNIFORM_BASELINE == pytest.approx(expected, rel=1e-6)

    def test_valid_api_categories_includes_general(self):
        """API categories should include 'general' fallback."""
        from python_app.categories import VALID_API_CATEGORIES, CONNECT3_CATEGORIES_SET
        
        assert "general" in VALID_API_CATEGORIES
        assert VALID_API_CATEGORIES == CONNECT3_CATEGORIES_SET | {"general"}


class TestCategoryDescriptions:
    """Tests for category descriptions."""

    def test_all_categories_have_descriptions(self):
        """Every category should have a description."""
        from python_app.categories import CONNECT3_CATEGORIES, CATEGORY_DESCRIPTIONS
        
        for cat in CONNECT3_CATEGORIES:
            assert cat in CATEGORY_DESCRIPTIONS, f"Missing description for {cat}"
            assert len(CATEGORY_DESCRIPTIONS[cat]) > 10, f"Description too short for {cat}"

    def test_descriptions_are_non_empty_strings(self):
        """All descriptions should be non-empty strings."""
        from python_app.categories import CATEGORY_DESCRIPTIONS
        
        for cat, desc in CATEGORY_DESCRIPTIONS.items():
            assert isinstance(desc, str)
            assert len(desc.strip()) > 0

    def test_no_extra_descriptions(self):
        """No descriptions for categories that don't exist."""
        from python_app.categories import CONNECT3_CATEGORIES_SET, CATEGORY_DESCRIPTIONS
        
        for cat in CATEGORY_DESCRIPTIONS.keys():
            assert cat in CONNECT3_CATEGORIES_SET, f"Extra description for {cat}"


class TestCategoryUsage:
    """Tests for category usage patterns."""

    def test_categories_can_be_iterated(self):
        """Categories list should be iterable."""
        from python_app.categories import CONNECT3_CATEGORIES, NUM_CATEGORIES
        
        count = 0
        for cat in CONNECT3_CATEGORIES:
            count += 1
        assert count == NUM_CATEGORIES

    def test_category_lookup_is_fast(self):
        """Set lookup should work correctly."""
        from python_app.categories import CONNECT3_CATEGORIES_SET
        
        assert "tech_innovation" in CONNECT3_CATEGORIES_SET
        assert "invalid_category" not in CONNECT3_CATEGORIES_SET

    def test_expected_categories_present(self):
        """Key expected categories should be present."""
        from python_app.categories import CONNECT3_CATEGORIES_SET
        
        expected = [
            "tech_innovation",
            "career_networking",
            "academic_workshops",
            "social_cultural",
            "sports_fitness",
            "gaming_esports",
        ]
        for cat in expected:
            assert cat in CONNECT3_CATEGORIES_SET, f"Missing expected category: {cat}"
