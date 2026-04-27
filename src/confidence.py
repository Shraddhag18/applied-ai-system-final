"""
Confidence scoring and self-critique for the Music Recommender.

ConfidenceScorer evaluates how trustworthy a set of recommendations is,
considering score quality, catalog coverage, profile coherence, and
result diversity. Low confidence triggers suggestions for improvement.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class ConfidenceResult:
    overall: float                  # 0.0–1.0
    level: str                      # HIGH, MEDIUM, LOW
    components: Dict[str, float]    # individual confidence factors
    critique: List[str]             # specific issues found
    suggestions: List[str]          # actionable improvement ideas

    def summary(self) -> str:
        lines = [f"Confidence: {self.overall:.2f} ({self.level})"]
        for name, val in self.components.items():
            lines.append(f"  {name}: {val:.2f}")
        if self.critique:
            lines.append("Critique:")
            for c in self.critique:
                lines.append(f"  - {c}")
        if self.suggestions:
            lines.append("Suggestions:")
            for s in self.suggestions:
                lines.append(f"  - {s}")
        return "\n".join(lines)


class ConfidenceScorer:
    """
    Evaluates recommendation confidence using multiple signals.

    Confidence factors:
      - Score quality: How close is the top score to the maximum possible?
      - Score spread: Is there a healthy distribution, or does one song dominate?
      - Genre coverage: Does the catalog have enough songs in the user's genre?
      - Profile coherence: Are the user's preferences internally consistent?
    """

    def __init__(self, max_possible_score: float = 8.0):
        self.max_possible = max_possible_score

    def score_confidence(
        self,
        results: List[Tuple],
        user_prefs: Dict,
        songs: List[Dict],
        genre_context=None,
    ) -> ConfidenceResult:
        components: Dict[str, float] = {}
        critique: List[str] = []
        suggestions: List[str] = []

        # Factor 1: Score quality (top score as fraction of max)
        if results:
            top_score = results[0][1]
            score_quality = min(1.0, top_score / self.max_possible)
        else:
            score_quality = 0.0
            critique.append("No results generated")
        components["score_quality"] = round(score_quality, 2)

        # Factor 2: Score spread (ratio of mean to top; closer to 1 = more even)
        if len(results) >= 2:
            scores = [s for _, s, _ in results]
            mean_score = sum(scores) / len(scores)
            top = scores[0]
            spread = mean_score / top if top > 0 else 0.0
            if spread < 0.5:
                critique.append(
                    f"Large gap between #1 ({top:.2f}) and average ({mean_score:.2f}) — "
                    f"catalog may lack depth for this profile"
                )
                suggestions.append("Try diversity filter to surface alternative genres")
        else:
            spread = 0.5
        components["score_spread"] = round(spread, 2)

        # Factor 3: Genre coverage
        user_genre = user_prefs.get("favorite_genre", "")
        genre_songs = [s for s in songs if s.get("genre") == user_genre]
        genre_count = len(genre_songs)
        if genre_count == 0:
            genre_cov = 0.0
            critique.append(f"Genre '{user_genre}' is not in the catalog at all")
            suggestions.append(f"No '{user_genre}' songs available — showing best alternatives")
        elif genre_count == 1:
            genre_cov = 0.4
            critique.append(f"Only 1 '{user_genre}' song in catalog — results will be repetitive")
        elif genre_count <= 3:
            genre_cov = 0.7
        else:
            genre_cov = 1.0
        components["genre_coverage"] = round(genre_cov, 2)

        # Factor 4: Profile coherence
        coherence = 1.0
        target_energy = user_prefs.get("target_energy", 0.5)
        likes_acoustic = user_prefs.get("likes_acoustic", False)
        mood = user_prefs.get("favorite_mood", "")

        # Check energy vs genre typical range
        if genre_context and hasattr(genre_context, "typical_energy"):
            lo, hi = genre_context.typical_energy
            if target_energy < lo - 0.15 or target_energy > hi + 0.15:
                coherence -= 0.3
                critique.append(
                    f"Energy {target_energy:.2f} conflicts with '{user_genre}' "
                    f"typical range [{lo:.1f}-{hi:.1f}]"
                )
                suggestions.append("Consider adjusting energy target or trying a different genre")

        if likes_acoustic and target_energy > 0.8:
            coherence -= 0.2
            critique.append("Acoustic preference with high energy is unusual")

        low_e_moods = {"chill", "relaxed", "sad", "melancholic"}
        high_e_moods = {"energetic", "intense", "angry"}
        if mood in low_e_moods and target_energy > 0.85:
            coherence -= 0.2
        if mood in high_e_moods and target_energy < 0.3:
            coherence -= 0.2

        coherence = max(0.0, coherence)
        components["profile_coherence"] = round(coherence, 2)

        # Weighted overall confidence
        overall = (
            0.3 * score_quality +
            0.2 * spread +
            0.25 * genre_cov +
            0.25 * coherence
        )
        overall = round(min(1.0, max(0.0, overall)), 2)

        if overall >= 0.7:
            level = "HIGH"
        elif overall >= 0.4:
            level = "MEDIUM"
        else:
            level = "LOW"
            if not suggestions:
                suggestions.append("Try a different scoring mode for better results")

        return ConfidenceResult(
            overall=overall, level=level, components=components,
            critique=critique, suggestions=suggestions,
        )

    def self_critique(
        self,
        results: List[Tuple],
        user_prefs: Dict,
        songs: List[Dict],
        genre_context=None,
    ) -> str:
        """Return a human-readable self-critique of the recommendations."""
        conf = self.score_confidence(results, user_prefs, songs, genre_context)
        return conf.summary()
