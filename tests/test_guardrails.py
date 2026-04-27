"""Tests for input validation guardrails and output quality checks."""

import pytest
from src.guardrails import InputValidator, OutputGuardrail


class TestInputValidator:
    @pytest.fixture
    def validator(self):
        return InputValidator()

    def test_valid_profile(self, validator):
        prefs = {"favorite_genre": "pop", "favorite_mood": "happy",
                 "target_energy": 0.8, "likes_acoustic": False}
        result = validator.validate(prefs)
        assert result.is_valid

    def test_missing_genre(self, validator):
        prefs = {"favorite_mood": "happy", "target_energy": 0.8}
        result = validator.validate(prefs)
        assert not result.is_valid
        assert any("genre" in e.lower() for e in result.errors)

    def test_missing_mood(self, validator):
        prefs = {"favorite_genre": "pop", "target_energy": 0.8}
        result = validator.validate(prefs)
        assert not result.is_valid

    def test_missing_energy(self, validator):
        prefs = {"favorite_genre": "pop", "favorite_mood": "happy"}
        result = validator.validate(prefs)
        assert not result.is_valid

    def test_energy_out_of_range(self, validator):
        prefs = {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 1.5}
        result = validator.validate(prefs)
        assert not result.is_valid

    def test_negative_energy(self, validator):
        prefs = {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": -0.1}
        result = validator.validate(prefs)
        assert not result.is_valid

    def test_unknown_mood_warning(self, validator):
        prefs = {"favorite_genre": "pop", "favorite_mood": "groovy", "target_energy": 0.5}
        result = validator.validate(prefs)
        assert result.is_valid  # still valid, just a warning
        assert len(result.warnings) > 0

    def test_empty_genre_invalid(self, validator):
        prefs = {"favorite_genre": "", "favorite_mood": "happy", "target_energy": 0.5}
        result = validator.validate(prefs)
        assert not result.is_valid


class TestOutputGuardrail:
    @pytest.fixture
    def guardrail(self):
        return OutputGuardrail()

    def test_good_results_pass(self, guardrail):
        results = [
            ({"genre": "pop", "title": "A"}, 6.0, "genre match"),
            ({"genre": "pop", "title": "B"}, 5.0, "mood match"),
            ({"genre": "lofi", "title": "C"}, 4.0, "energy match"),
        ]
        check = guardrail.check(results, max_possible_score=8.0,
                                catalog_genres=["pop", "lofi"], user_genre="pop")
        assert check.passed

    def test_low_score_warning(self, guardrail):
        results = [
            ({"genre": "pop", "title": "A"}, 1.0, "weak match"),
            ({"genre": "pop", "title": "B"}, 0.8, "weak match"),
            ({"genre": "pop", "title": "C"}, 0.5, "weak match"),
        ]
        check = guardrail.check(results, max_possible_score=8.0)
        assert not check.passed

    def test_missing_genre_warning(self, guardrail):
        results = [
            ({"genre": "pop", "title": "A"}, 5.0, "match"),
            ({"genre": "pop", "title": "B"}, 4.0, "match"),
            ({"genre": "pop", "title": "C"}, 3.0, "match"),
        ]
        check = guardrail.check(results, catalog_genres=["pop", "rock"], user_genre="k-pop")
        assert "k-pop" in check.checks.get(f"Genre 'k-pop' in catalog", True).__class__.__name__ or \
               any("k-pop" in w for w in check.warnings)

    def test_empty_results_fail(self, guardrail):
        check = guardrail.check([])
        assert not check.passed

    def test_no_diversity_warning(self, guardrail):
        results = [
            ({"genre": "pop", "title": "A"}, 5.0, "match"),
            ({"genre": "pop", "title": "B"}, 4.0, "match"),
            ({"genre": "pop", "title": "C"}, 3.0, "match"),
        ]
        check = guardrail.check(results)
        assert any("diversity" in s.lower() for s in check.suggestions) or \
               not check.checks.get("Genre diversity in results", True)
