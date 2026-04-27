"""
Input validation and output quality guardrails for the Music Recommender.

InputValidator:  Validates user profiles before scoring
OutputGuardrail: Checks recommendation quality after scoring
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = []
        if self.errors:
            lines.append(f"ERRORS: {'; '.join(self.errors)}")
        if self.warnings:
            lines.append(f"WARNINGS: {'; '.join(self.warnings)}")
        if not lines:
            lines.append("All checks passed.")
        return "\n".join(lines)


@dataclass
class QualityCheckResult:
    passed: bool
    checks: Dict[str, bool] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = []
        for check, passed in self.checks.items():
            status = "PASS" if passed else "FAIL"
            lines.append(f"  [{status}] {check}")
        if self.warnings:
            lines.append(f"  Warnings: {'; '.join(self.warnings)}")
        if self.suggestions:
            lines.append(f"  Suggestions: {'; '.join(self.suggestions)}")
        return "\n".join(lines)


class InputValidator:
    """Validates user preferences before they enter the scoring pipeline."""

    VALID_MOODS = {
        "happy", "chill", "intense", "relaxed", "moody", "focused",
        "romantic", "nostalgic", "sad", "energetic", "melancholic", "angry"
    }

    def validate(self, user_prefs: Dict) -> ValidationResult:
        errors: List[str] = []
        warnings: List[str] = []

        # Required fields
        genre = user_prefs.get("favorite_genre", "")
        if not genre or not isinstance(genre, str):
            errors.append("favorite_genre is required and must be a non-empty string")

        mood = user_prefs.get("favorite_mood", "")
        if not mood or not isinstance(mood, str):
            errors.append("favorite_mood is required and must be a non-empty string")
        elif mood.lower() not in self.VALID_MOODS:
            warnings.append(f"Mood '{mood}' is not in standard taxonomy — soft matching may be limited")

        # Energy range
        energy = user_prefs.get("target_energy")
        if energy is None:
            errors.append("target_energy is required")
        elif not isinstance(energy, (int, float)):
            errors.append("target_energy must be a number")
        elif energy < 0.0 or energy > 1.0:
            errors.append(f"target_energy must be between 0.0 and 1.0 (got {energy})")

        # Acoustic preference
        acoustic = user_prefs.get("likes_acoustic")
        if acoustic is not None and not isinstance(acoustic, bool):
            warnings.append("likes_acoustic should be a boolean (True/False)")

        # Optional: popularity range
        pop = user_prefs.get("target_popularity")
        if pop is not None:
            if not isinstance(pop, (int, float)) or pop < 0 or pop > 100:
                warnings.append(f"target_popularity should be 0-100 (got {pop})")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )


class OutputGuardrail:
    """Checks recommendation output quality and flags potential issues."""

    def __init__(self, min_score_ratio: float = 0.3, min_results: int = 3):
        self.min_score_ratio = min_score_ratio
        self.min_results = min_results

    def check(self, results: List[Tuple], max_possible_score: float = 8.0,
              catalog_genres: List[str] = None,
              user_genre: str = "") -> QualityCheckResult:
        checks: Dict[str, bool] = {}
        warnings: List[str] = []
        suggestions: List[str] = []

        # Check 1: Sufficient results
        has_enough = len(results) >= self.min_results
        checks["Sufficient results returned"] = has_enough
        if not has_enough:
            warnings.append(f"Only {len(results)} results (minimum: {self.min_results})")

        # Check 2: Score quality
        if results:
            top_score = results[0][1]
            score_ratio = top_score / max_possible_score if max_possible_score > 0 else 0
            good_score = score_ratio >= self.min_score_ratio
            checks[f"Top score quality ({score_ratio:.0%} of max)"] = good_score
            if not good_score:
                warnings.append(f"Top score is only {score_ratio:.0%} of maximum possible")
                suggestions.append("Try a different scoring mode or broaden preferences")
        else:
            checks["Top score quality"] = False
            warnings.append("No results to evaluate")

        # Check 3: Genre representation
        if user_genre and catalog_genres is not None:
            genre_present = user_genre in catalog_genres
            checks[f"Genre '{user_genre}' in catalog"] = genre_present
            if not genre_present:
                warnings.append(f"Genre '{user_genre}' not found in catalog")
                suggestions.append("Consider exploring related genres")

        # Check 4: All results have explanations
        if results:
            all_explained = all(expl and expl.strip() for _, _, expl in results)
            checks["All results have explanations"] = all_explained
            if not all_explained:
                warnings.append("Some results lack explanations")

        # Check 5: Diversity (not all same genre)
        if results:
            genres_in_results = {song.get("genre", "") for song, _, _ in results}
            diverse = len(genres_in_results) >= 2 or len(results) <= 2
            checks["Genre diversity in results"] = diverse
            if not diverse:
                suggestions.append("Enable diversity filter to break genre bubble")

        passed = all(checks.values())
        return QualityCheckResult(passed=passed, checks=checks,
                                  warnings=warnings, suggestions=suggestions)
