"""
RAG-style knowledge retrieval for the Music Recommender.

Provides soft matching capabilities by loading external knowledge bases:
  - MoodRetriever:  graduated mood similarity (replaces binary mood matching)
  - GenreRetriever: related genre discovery (replaces exact-only genre matching)
  - KnowledgeBase:  unified interface for all retrieval operations

The knowledge bases are stored as JSON files in data/knowledge_base/ and are
loaded once at startup. This keeps the system self-contained (no external APIs)
while demonstrating the RAG pattern of separating knowledge from logic.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data classes for retrieval results
# ---------------------------------------------------------------------------

@dataclass
class MoodContext:
    """Context retrieved about mood similarity."""
    query_mood: str
    similar_moods: Dict[str, float]  # mood -> similarity score (0.0–1.0)
    description: str = ""

    def similarity_to(self, other_mood: str) -> float:
        """Return similarity score between query mood and another mood."""
        return self.similar_moods.get(other_mood, 0.0)


@dataclass
class GenreContext:
    """Context retrieved about genre relationships."""
    query_genre: str
    related_genres: Dict[str, float]  # genre -> similarity score (0.0–1.0)
    description: str = ""
    typical_energy: Tuple[float, float] = (0.0, 1.0)
    typical_moods: List[str] = field(default_factory=list)

    def similarity_to(self, other_genre: str) -> float:
        """Return similarity score between query genre and another genre."""
        return self.related_genres.get(other_genre, 0.0)

    def is_energy_typical(self, energy: float) -> bool:
        """Check if an energy level falls within the genre's typical range."""
        return self.typical_energy[0] <= energy <= self.typical_energy[1]


@dataclass
class RetrievalContext:
    """Combined context from all knowledge retrievers."""
    mood_context: Optional[MoodContext] = None
    genre_context: Optional[GenreContext] = None
    warnings: List[str] = field(default_factory=list)

    @property
    def has_mood(self) -> bool:
        return self.mood_context is not None

    @property
    def has_genre(self) -> bool:
        return self.genre_context is not None


# ---------------------------------------------------------------------------
# Mood Retriever
# ---------------------------------------------------------------------------

class MoodRetriever:
    """
    Retrieves mood similarity data from the mood taxonomy knowledge base.

    The taxonomy maps each mood to every other mood with a similarity score
    from 0.0 (unrelated) to 1.0 (identical). This enables soft mood matching
    where 'chill' and 'relaxed' receive partial credit instead of being
    treated as completely different.
    """

    def __init__(self, taxonomy_path: str):
        self._moods: Dict[str, dict] = {}
        self._load(taxonomy_path)

    def _load(self, path: str) -> None:
        """Load and validate the mood taxonomy JSON file."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Mood taxonomy not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in mood taxonomy: {e}")

        if "moods" not in data:
            raise ValueError("Mood taxonomy missing 'moods' key")

        self._moods = data["moods"]

    def retrieve(self, mood: str) -> MoodContext:
        """
        Retrieve similarity context for a given mood.

        If the mood is not in the taxonomy, returns a context with zero
        similarity to everything (graceful degradation).
        """
        mood_lower = mood.lower().strip()
        if mood_lower in self._moods:
            entry = self._moods[mood_lower]
            return MoodContext(
                query_mood=mood_lower,
                similar_moods=entry.get("similar", {}),
                description=entry.get("description", ""),
            )
        # Unknown mood — return empty context (no crash, no partial matches)
        return MoodContext(
            query_mood=mood_lower,
            similar_moods={mood_lower: 1.0},  # self-similarity only
            description=f"Unknown mood: {mood_lower}",
        )

    def similarity(self, mood_a: str, mood_b: str) -> float:
        """Return the similarity score between two moods (0.0–1.0)."""
        mood_a = mood_a.lower().strip()
        mood_b = mood_b.lower().strip()
        if mood_a == mood_b:
            return 1.0
        ctx = self.retrieve(mood_a)
        return ctx.similarity_to(mood_b)

    @property
    def known_moods(self) -> List[str]:
        """Return all moods in the taxonomy."""
        return list(self._moods.keys())


# ---------------------------------------------------------------------------
# Genre Retriever
# ---------------------------------------------------------------------------

class GenreRetriever:
    """
    Retrieves genre relationship data from the genre guides knowledge base.

    Each genre maps to related genres with similarity scores, plus metadata
    about typical energy ranges and moods. This enables soft genre matching
    and energy-coherence detection.
    """

    def __init__(self, guides_path: str):
        self._genres: Dict[str, dict] = {}
        self._load(guides_path)

    def _load(self, path: str) -> None:
        """Load and validate the genre guides JSON file."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Genre guides not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in genre guides: {e}")

        if "genres" not in data:
            raise ValueError("Genre guides missing 'genres' key")

        self._genres = data["genres"]

    def retrieve(self, genre: str) -> GenreContext:
        """
        Retrieve relationship context for a given genre.

        If the genre is not in the knowledge base, returns a context with
        zero similarity to everything (graceful degradation).
        """
        genre_lower = genre.lower().strip()
        if genre_lower in self._genres:
            entry = self._genres[genre_lower]
            typical_energy = tuple(entry.get("typical_energy", [0.0, 1.0]))
            return GenreContext(
                query_genre=genre_lower,
                related_genres=entry.get("related", {}),
                description=entry.get("description", ""),
                typical_energy=typical_energy,
                typical_moods=entry.get("typical_moods", []),
            )
        # Unknown genre — return empty context
        return GenreContext(
            query_genre=genre_lower,
            related_genres={genre_lower: 1.0},  # self-similarity only
            description=f"Unknown genre: {genre_lower} (not in knowledge base)",
            typical_energy=(0.0, 1.0),
            typical_moods=[],
        )

    def similarity(self, genre_a: str, genre_b: str) -> float:
        """Return the similarity score between two genres (0.0–1.0)."""
        genre_a = genre_a.lower().strip()
        genre_b = genre_b.lower().strip()
        if genre_a == genre_b:
            return 1.0
        ctx = self.retrieve(genre_a)
        return ctx.similarity_to(genre_b)

    def is_genre_known(self, genre: str) -> bool:
        """Check if a genre exists in the knowledge base."""
        return genre.lower().strip() in self._genres

    @property
    def known_genres(self) -> List[str]:
        """Return all genres in the knowledge base."""
        return list(self._genres.keys())


# ---------------------------------------------------------------------------
# Unified Knowledge Base
# ---------------------------------------------------------------------------

class KnowledgeBase:
    """
    Unified interface for all knowledge retrieval operations.

    Wraps MoodRetriever and GenreRetriever into a single entry point.
    This is the main class that other modules (agent, recommender) interact
    with for knowledge-augmented recommendations.
    """

    def __init__(self, knowledge_dir: str = "data/knowledge_base"):
        mood_path = os.path.join(knowledge_dir, "mood_taxonomy.json")
        genre_path = os.path.join(knowledge_dir, "genre_guides.json")

        self.mood_retriever = MoodRetriever(mood_path)
        self.genre_retriever = GenreRetriever(genre_path)

    def retrieve_context(self, user_prefs: dict) -> RetrievalContext:
        """
        Retrieve all relevant knowledge context for a user profile.

        Args:
            user_prefs: dict with keys like 'favorite_genre', 'favorite_mood', etc.

        Returns:
            RetrievalContext with mood and genre context plus any warnings.
        """
        warnings: List[str] = []
        mood_ctx = None
        genre_ctx = None

        # Retrieve mood context
        fav_mood = user_prefs.get("favorite_mood", "")
        if fav_mood:
            mood_ctx = self.mood_retriever.retrieve(fav_mood)
            if fav_mood.lower() not in self.mood_retriever.known_moods:
                warnings.append(
                    f"Mood '{fav_mood}' not in taxonomy — soft matching disabled for mood"
                )

        # Retrieve genre context
        fav_genre = user_prefs.get("favorite_genre", "")
        if fav_genre:
            genre_ctx = self.genre_retriever.retrieve(fav_genre)
            if not self.genre_retriever.is_genre_known(fav_genre):
                warnings.append(
                    f"Genre '{fav_genre}' not in knowledge base — "
                    f"no songs in catalog will match by genre"
                )

            # Check energy coherence
            target_energy = user_prefs.get("target_energy", 0.5)
            if genre_ctx and not genre_ctx.is_energy_typical(target_energy):
                warnings.append(
                    f"Target energy {target_energy:.2f} is outside typical range "
                    f"{genre_ctx.typical_energy} for genre '{fav_genre}' — "
                    f"this may indicate conflicting preferences"
                )

        return RetrievalContext(
            mood_context=mood_ctx,
            genre_context=genre_ctx,
            warnings=warnings,
        )

    def mood_similarity(self, mood_a: str, mood_b: str) -> float:
        """Convenience: return mood similarity score."""
        return self.mood_retriever.similarity(mood_a, mood_b)

    def genre_similarity(self, genre_a: str, genre_b: str) -> float:
        """Convenience: return genre similarity score."""
        return self.genre_retriever.similarity(genre_a, genre_b)
