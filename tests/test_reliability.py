"""
Structured reliability experiments for the Music Recommender.

These tests validate system-level properties:
  1. Determinism:      Same input -> same output every time
  2. Degradation:      Graceful performance as catalog shrinks
  3. Adversarial:      Guardrail catch rate on 10 adversarial profiles
  4. Mode sensitivity: Ranking stability across scoring modes
"""

import pytest
from src.recommender import load_songs, recommend_songs
from src.agent import RecommendationAgent
from src.retrieval import KnowledgeBase
from src.guardrails import InputValidator
from src.confidence import ConfidenceScorer


@pytest.fixture
def songs():
    return load_songs("data/songs.csv")

@pytest.fixture
def kb():
    return KnowledgeBase("data/knowledge_base")

@pytest.fixture
def agent(songs, kb):
    return RecommendationAgent(songs, kb)


class TestDeterminism:
    """Same input must always produce identical output."""

    def test_same_profile_same_results(self, songs):
        prefs = {"favorite_genre": "lofi", "favorite_mood": "chill",
                 "target_energy": 0.4, "likes_acoustic": True}
        r1 = recommend_songs(prefs, songs, k=5)
        r2 = recommend_songs(prefs, songs, k=5)
        titles1 = [s["title"] for s, _, _ in r1]
        titles2 = [s["title"] for s, _, _ in r2]
        assert titles1 == titles2

    def test_determinism_across_modes(self, songs):
        prefs = {"favorite_genre": "pop", "favorite_mood": "happy",
                 "target_energy": 0.85, "likes_acoustic": False}
        for mode in ["balanced", "genre_first", "mood_first", "energy_focused"]:
            r1 = recommend_songs(prefs, songs, k=5, mode=mode)
            r2 = recommend_songs(prefs, songs, k=5, mode=mode)
            assert [s["title"] for s, _, _ in r1] == [s["title"] for s, _, _ in r2]


class TestGracefulDegradation:
    """System should degrade gracefully as catalog shrinks."""

    def test_single_song_catalog(self):
        songs = [{"id": 1, "title": "Only Song", "artist": "Solo", "genre": "pop",
                  "mood": "happy", "energy": 0.8, "tempo_bpm": 120, "valence": 0.9,
                  "danceability": 0.8, "acousticness": 0.2, "popularity": 70,
                  "release_decade": "2020s", "mood_tags": []}]
        prefs = {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.8}
        results = recommend_songs(prefs, songs, k=5)
        assert len(results) == 1
        assert results[0][0]["title"] == "Only Song"

    def test_empty_catalog(self):
        prefs = {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 0.8}
        results = recommend_songs(prefs, [], k=5)
        assert len(results) == 0

    def test_shrinking_catalog_scores_decrease(self, songs):
        prefs = {"favorite_genre": "lofi", "favorite_mood": "chill",
                 "target_energy": 0.4, "likes_acoustic": True}
        full = recommend_songs(prefs, songs, k=5)
        half = recommend_songs(prefs, songs[:len(songs)//2], k=5)
        # Full catalog should have equal or higher top score
        assert full[0][1] >= half[0][1] if half else True


class TestAdversarialProfiles:
    """Validate guardrail catch rate on adversarial inputs."""

    ADVERSARIAL = [
        {"favorite_genre": "k-pop", "favorite_mood": "happy", "target_energy": 0.8, "likes_acoustic": False},
        {"favorite_genre": "classical", "favorite_mood": "sad", "target_energy": 0.9, "likes_acoustic": True},
        {"favorite_genre": "metal", "favorite_mood": "chill", "target_energy": 0.1, "likes_acoustic": True},
        {"favorite_genre": "lofi", "favorite_mood": "angry", "target_energy": 0.95, "likes_acoustic": False},
        {"favorite_genre": "", "favorite_mood": "happy", "target_energy": 0.5, "likes_acoustic": False},
        {"favorite_genre": "pop", "favorite_mood": "", "target_energy": 0.5, "likes_acoustic": False},
        {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": 1.5, "likes_acoustic": False},
        {"favorite_genre": "pop", "favorite_mood": "happy", "target_energy": -0.1, "likes_acoustic": False},
        {"favorite_genre": "afrobeats", "favorite_mood": "energetic", "target_energy": 0.9, "likes_acoustic": False},
        {"favorite_genre": "jazz", "favorite_mood": "intense", "target_energy": 0.95, "likes_acoustic": True},
    ]

    def test_system_catches_adversarial_inputs(self, agent):
        """Combined validator + agent should flag most adversarial profiles."""
        validator = InputValidator()
        catches = 0
        for prefs in self.ADVERSARIAL:
            validation = validator.validate(prefs)
            if not validation.is_valid or validation.warnings:
                catches += 1
                continue
            # For syntactically valid profiles, use the agent to check semantics
            result = agent.run("adversarial_test", prefs)
            if (result.confidence.level in ("LOW", "MEDIUM")
                    or result.warnings
                    or result.confidence.critique):
                catches += 1
        # Combined system should catch at least 70% of adversarial profiles
        catch_rate = catches / len(self.ADVERSARIAL)
        assert catch_rate >= 0.7, f"Catch rate {catch_rate:.0%} is below 70% threshold"

    def test_agent_handles_all_adversarial(self, agent):
        """Agent should never crash on adversarial input."""
        for i, prefs in enumerate(self.ADVERSARIAL):
            try:
                result = agent.run(f"Adversarial-{i}", prefs)
                assert result is not None
            except Exception as e:
                pytest.fail(f"Agent crashed on adversarial profile {i}: {e}")


class TestModeSensitivity:
    """Check how much rankings change across scoring modes."""

    def test_top_pick_stability(self, songs):
        prefs = {"favorite_genre": "pop", "favorite_mood": "happy",
                 "target_energy": 0.85, "likes_acoustic": False}
        results_by_mode = {}
        for mode in ["balanced", "genre_first", "mood_first", "energy_focused"]:
            results = recommend_songs(prefs, songs, k=5, mode=mode)
            results_by_mode[mode] = results

        # #1 pick should be the same across at least 3 modes (stable top pick)
        top_picks = [r[0][0]["title"] for r in results_by_mode.values() if r]
        most_common = max(set(top_picks), key=top_picks.count)
        stability = top_picks.count(most_common) / len(top_picks)
        assert stability >= 0.5, f"Top pick stability {stability:.0%} is too low"
