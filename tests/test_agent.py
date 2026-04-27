"""Tests for the agentic recommendation planning loop."""

import pytest
from src.agent import RecommendationAgent, PlanStep
from src.recommender import load_songs
from src.retrieval import KnowledgeBase


@pytest.fixture
def agent():
    songs = load_songs("data/songs.csv")
    kb = KnowledgeBase("data/knowledge_base")
    return RecommendationAgent(songs, kb)


class TestAgentBasicFlow:
    def test_agent_returns_results(self, agent):
        prefs = {"favorite_genre": "lofi", "favorite_mood": "chill",
                 "target_energy": 0.4, "likes_acoustic": True}
        result = agent.run("Lofi Fan", prefs)
        assert len(result.recommendations) == 5
        assert result.confidence.level in ("HIGH", "MEDIUM", "LOW")

    def test_agent_log_has_all_steps(self, agent):
        prefs = {"favorite_genre": "pop", "favorite_mood": "happy",
                 "target_energy": 0.8, "likes_acoustic": False}
        result = agent.run("Pop Fan", prefs)
        step_types = [s.step for s in result.log.steps]
        assert PlanStep.ANALYZE in step_types
        assert PlanStep.RETRIEVE in step_types
        assert PlanStep.SCORE in step_types
        assert PlanStep.CRITIQUE in step_types
        assert PlanStep.EXPLAIN in step_types

    def test_agent_log_summary(self, agent):
        prefs = {"favorite_genre": "pop", "favorite_mood": "happy",
                 "target_energy": 0.8, "likes_acoustic": False}
        result = agent.run("Pop Fan", prefs)
        summary = result.log.summary()
        assert "Pop Fan" in summary
        assert "ANALYZE" in summary


class TestAgentAdversarialProfiles:
    def test_unknown_genre_detected(self, agent):
        prefs = {"favorite_genre": "k-pop", "favorite_mood": "happy",
                 "target_energy": 0.8, "likes_acoustic": False}
        result = agent.run("K-pop Fan", prefs)
        all_warnings = result.warnings
        assert any("k-pop" in w.lower() for w in all_warnings)

    def test_contradictory_profile_low_confidence(self, agent):
        prefs = {"favorite_genre": "classical", "favorite_mood": "sad",
                 "target_energy": 0.9, "likes_acoustic": True}
        result = agent.run("Conflicted", prefs)
        # Contradictory profile should not have HIGH confidence
        assert result.confidence.level in ("LOW", "MEDIUM")

    def test_agent_still_returns_results_for_bad_profile(self, agent):
        prefs = {"favorite_genre": "k-pop", "favorite_mood": "happy",
                 "target_energy": 0.8, "likes_acoustic": False}
        result = agent.run("K-pop Fan", prefs)
        assert len(result.recommendations) > 0  # graceful degradation


class TestAgentValidation:
    def test_invalid_profile_returns_empty(self, agent):
        prefs = {"favorite_genre": "", "favorite_mood": "", "target_energy": 1.5}
        result = agent.run("Invalid", prefs)
        assert len(result.recommendations) == 0
        assert result.confidence.level == "LOW"

    def test_valid_profile_has_confidence(self, agent):
        prefs = {"favorite_genre": "pop", "favorite_mood": "happy",
                 "target_energy": 0.8, "likes_acoustic": False}
        result = agent.run("Pop Fan", prefs)
        assert result.confidence.overall > 0


class TestAgentRefinement:
    def test_refinement_changes_mode_when_low_confidence(self, agent):
        # This profile should trigger refinement due to missing genre
        prefs = {"favorite_genre": "k-pop", "favorite_mood": "happy",
                 "target_energy": 0.8, "likes_acoustic": False}
        result = agent.run("K-pop Fan", prefs)
        # Check that refinement step exists in log
        refine_steps = [s for s in result.log.steps if s.step == PlanStep.REFINE]
        assert len(refine_steps) >= 1
