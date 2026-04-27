"""Tests for the bias detection and fairness evaluation module."""

import pytest
from src.bias_detector import BiasDetector


def make_songs():
    return [
        {"id": 1, "title": "Song A", "artist": "Art1", "genre": "pop", "mood": "happy", "energy": 0.8},
        {"id": 2, "title": "Song B", "artist": "Art1", "genre": "pop", "mood": "happy", "energy": 0.7},
        {"id": 3, "title": "Song C", "artist": "Art2", "genre": "lofi", "mood": "chill", "energy": 0.3},
        {"id": 4, "title": "Song D", "artist": "Art3", "genre": "rock", "mood": "intense", "energy": 0.9},
    ]


class TestGenreCoverage:
    def test_basic_coverage(self):
        bd = BiasDetector()
        result = bd.genre_coverage(make_songs())
        assert result.total_songs == 4
        assert result.genre_counts["pop"] == 2
        assert result.genre_counts["lofi"] == 1

    def test_underrepresented_detection(self):
        bd = BiasDetector()
        result = bd.genre_coverage(make_songs())
        assert "lofi" in result.underrepresented
        assert "rock" in result.underrepresented
        assert "pop" not in result.underrepresented

    def test_missing_genre_detection(self):
        bd = BiasDetector()
        result = bd.genre_coverage(make_songs(), profile_genres=["k-pop", "pop"])
        assert "k-pop" in result.missing_from_catalog
        assert "pop" not in result.missing_from_catalog


class TestGenreLockout:
    def test_no_lockout(self):
        bd = BiasDetector()
        result = bd.genre_lockout("test", {"favorite_genre": "pop"}, make_songs())
        assert not result.lockout_detected
        assert result.songs_in_genre == 2

    def test_lockout_detected(self):
        bd = BiasDetector()
        result = bd.genre_lockout("test", {"favorite_genre": "k-pop"}, make_songs())
        assert result.lockout_detected
        assert result.songs_in_genre == 0

    def test_single_song_warning(self):
        bd = BiasDetector()
        result = bd.genre_lockout("test", {"favorite_genre": "rock"}, make_songs())
        assert not result.lockout_detected
        assert "only 1" in result.message.lower()


class TestScoreDistribution:
    def test_even_distribution(self):
        bd = BiasDetector()
        results = [
            ({"genre": "pop"}, 5.0, "reason"),
            ({"genre": "lofi"}, 4.5, "reason"),
            ({"genre": "rock"}, 4.0, "reason"),
        ]
        dist = bd.score_distribution("test", results)
        assert not dist.is_dominant

    def test_dominant_distribution(self):
        bd = BiasDetector()
        results = [
            ({"genre": "pop"}, 8.0, "reason"),
            ({"genre": "lofi"}, 2.0, "reason"),
            ({"genre": "rock"}, 1.5, "reason"),
        ]
        dist = bd.score_distribution("test", results)
        assert dist.is_dominant
        assert dist.score_gap > 2.0

    def test_empty_results(self):
        bd = BiasDetector()
        dist = bd.score_distribution("test", [])
        assert not dist.is_dominant


class TestContradictionDetection:
    def test_no_contradictions(self):
        bd = BiasDetector()
        prefs = {"favorite_genre": "pop", "favorite_mood": "happy",
                 "target_energy": 0.8, "likes_acoustic": False}
        result = bd.detect_contradictions("test", prefs)
        assert result.severity == "none"

    def test_acoustic_high_energy_contradiction(self):
        bd = BiasDetector()
        prefs = {"favorite_genre": "pop", "favorite_mood": "happy",
                 "target_energy": 0.9, "likes_acoustic": True}
        result = bd.detect_contradictions("test", prefs)
        assert result.severity != "none"
        assert len(result.contradictions) >= 1

    def test_mood_energy_contradiction(self):
        bd = BiasDetector()
        prefs = {"favorite_genre": "pop", "favorite_mood": "chill",
                 "target_energy": 0.95, "likes_acoustic": False}
        result = bd.detect_contradictions("test", prefs)
        assert any("chill" in c for c in result.contradictions)


class TestDiversityIndex:
    def test_high_diversity(self):
        bd = BiasDetector()
        results = [
            ({"genre": "pop"}, 5.0, ""),
            ({"genre": "lofi"}, 4.5, ""),
            ({"genre": "rock"}, 4.0, ""),
            ({"genre": "jazz"}, 3.5, ""),
        ]
        div = bd.diversity_index("test", results)
        assert div.normalized_diversity >= 0.8

    def test_low_diversity(self):
        bd = BiasDetector()
        results = [
            ({"genre": "pop"}, 5.0, ""),
            ({"genre": "pop"}, 4.5, ""),
            ({"genre": "pop"}, 4.0, ""),
            ({"genre": "pop"}, 3.5, ""),
        ]
        div = bd.diversity_index("test", results)
        assert div.normalized_diversity == 0.0


class TestFairnessReport:
    def test_report_generation(self):
        bd = BiasDetector()
        songs = make_songs()
        profiles = {
            "pop_fan": {"favorite_genre": "pop", "favorite_mood": "happy",
                        "target_energy": 0.8, "likes_acoustic": False},
        }
        results = {
            "pop_fan": [({"genre": "pop"}, 5.0, "reason"), ({"genre": "lofi"}, 3.0, "reason")],
        }
        report = bd.fairness_report(profiles, songs, results)
        assert 0.0 <= report.overall_score <= 1.0
        assert len(report.lockouts) == 1
        assert len(report.summary) > 0
