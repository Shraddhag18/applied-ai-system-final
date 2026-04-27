"""Tests for the RAG-style knowledge retrieval module."""

import pytest
from src.retrieval import MoodRetriever, GenreRetriever, KnowledgeBase


KB_DIR = "data/knowledge_base"


class TestMoodRetriever:
    @pytest.fixture
    def retriever(self):
        return MoodRetriever(f"{KB_DIR}/mood_taxonomy.json")

    def test_self_similarity_is_one(self, retriever):
        assert retriever.similarity("chill", "chill") == 1.0

    def test_similar_moods_have_high_score(self, retriever):
        score = retriever.similarity("chill", "relaxed")
        assert score >= 0.7, f"chill/relaxed should be highly similar, got {score}"

    def test_opposite_moods_have_low_score(self, retriever):
        score = retriever.similarity("chill", "angry")
        assert score <= 0.1, f"chill/angry should be dissimilar, got {score}"

    def test_unknown_mood_returns_context(self, retriever):
        ctx = retriever.retrieve("funky")
        assert ctx.query_mood == "funky"
        assert ctx.similarity_to("funky") == 1.0
        assert ctx.similarity_to("happy") == 0.0

    def test_known_moods_list(self, retriever):
        moods = retriever.known_moods
        assert "happy" in moods
        assert "chill" in moods
        assert len(moods) >= 10

    def test_case_insensitive(self, retriever):
        score = retriever.similarity("CHILL", "relaxed")
        assert score >= 0.7


class TestGenreRetriever:
    @pytest.fixture
    def retriever(self):
        return GenreRetriever(f"{KB_DIR}/genre_guides.json")

    def test_self_similarity_is_one(self, retriever):
        assert retriever.similarity("pop", "pop") == 1.0

    def test_related_genres_have_score(self, retriever):
        score = retriever.similarity("pop", "indie pop")
        assert score >= 0.5, f"pop/indie pop should be related, got {score}"

    def test_unrelated_genres_low_score(self, retriever):
        score = retriever.similarity("metal", "lofi")
        assert score <= 0.1

    def test_unknown_genre_graceful(self, retriever):
        ctx = retriever.retrieve("k-pop")
        assert ctx.query_genre == "k-pop"
        assert "Unknown" in ctx.description

    def test_is_genre_known(self, retriever):
        assert retriever.is_genre_known("pop") is True
        assert retriever.is_genre_known("k-pop") is False

    def test_energy_typical_check(self, retriever):
        ctx = retriever.retrieve("lofi")
        assert ctx.is_energy_typical(0.35) is True
        assert ctx.is_energy_typical(0.95) is False


class TestKnowledgeBase:
    @pytest.fixture
    def kb(self):
        return KnowledgeBase(KB_DIR)

    def test_retrieve_context_normal(self, kb):
        prefs = {"favorite_genre": "lofi", "favorite_mood": "chill", "target_energy": 0.4}
        ctx = kb.retrieve_context(prefs)
        assert ctx.has_mood
        assert ctx.has_genre
        assert len(ctx.warnings) == 0

    def test_retrieve_context_unknown_genre(self, kb):
        prefs = {"favorite_genre": "k-pop", "favorite_mood": "happy", "target_energy": 0.8}
        ctx = kb.retrieve_context(prefs)
        assert any("k-pop" in w for w in ctx.warnings)

    def test_retrieve_context_energy_mismatch(self, kb):
        prefs = {"favorite_genre": "classical", "favorite_mood": "sad", "target_energy": 0.95}
        ctx = kb.retrieve_context(prefs)
        assert any("energy" in w.lower() for w in ctx.warnings)

    def test_mood_similarity_convenience(self, kb):
        score = kb.mood_similarity("chill", "relaxed")
        assert score >= 0.7

    def test_genre_similarity_convenience(self, kb):
        score = kb.genre_similarity("pop", "indie pop")
        assert score >= 0.5


class TestRetrievalErrors:
    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            MoodRetriever("nonexistent.json")

    def test_missing_genre_file_raises(self):
        with pytest.raises(FileNotFoundError):
            GenreRetriever("nonexistent.json")
