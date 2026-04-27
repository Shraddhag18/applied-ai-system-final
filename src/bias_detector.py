"""
Bias detection and fairness evaluation metrics for the Music Recommender.

Provides quantitative analysis of recommendation fairness:
  - Genre coverage / lockout detection
  - Score distribution analysis (dominance detection)
  - Contradiction detection (conflicting preferences)
  - Diversity index (Shannon entropy)
  - Comprehensive fairness report
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class CoverageResult:
    genre_counts: Dict[str, int]
    total_songs: int
    coverage_scores: Dict[str, float]
    underrepresented: List[str]
    missing_from_catalog: List[str]

    def summary(self) -> str:
        lines = [f"Catalog: {self.total_songs} songs across {len(self.genre_counts)} genres"]
        if self.underrepresented:
            lines.append(f"Underrepresented (<=1 song): {', '.join(self.underrepresented)}")
        if self.missing_from_catalog:
            lines.append(f"Missing from catalog: {', '.join(self.missing_from_catalog)}")
        return "\n".join(lines)


@dataclass
class LockoutResult:
    profile_name: str
    requested_genre: str
    genre_in_catalog: bool
    songs_in_genre: int
    lockout_detected: bool
    message: str


@dataclass
class DistributionResult:
    profile_name: str
    top_score: float
    second_score: float
    mean_score: float
    score_gap: float
    dominance_ratio: float
    is_dominant: bool
    message: str


@dataclass
class ContradictionResult:
    profile_name: str
    contradictions: List[str]
    severity: str  # "none", "mild", "severe"
    message: str


@dataclass
class DiversityResult:
    profile_name: str
    genre_distribution: Dict[str, int]
    shannon_entropy: float
    max_possible_entropy: float
    normalized_diversity: float
    message: str


@dataclass
class FairnessReport:
    coverage: CoverageResult
    lockouts: List[LockoutResult]
    distributions: List[DistributionResult]
    contradictions: List[ContradictionResult]
    diversities: List[DiversityResult]
    overall_score: float
    summary: str


class BiasDetector:
    """Analyzes recommendation results for bias, fairness, and quality issues."""

    def genre_coverage(self, songs: List[Dict], profile_genres: Optional[List[str]] = None) -> CoverageResult:
        genre_counts: Dict[str, int] = {}
        for song in songs:
            g = song.get("genre", "unknown")
            genre_counts[g] = genre_counts.get(g, 0) + 1
        total = len(songs)
        coverage_scores = {g: count / total for g, count in genre_counts.items()} if total > 0 else {}
        underrepresented = [g for g, count in genre_counts.items() if count <= 1]
        missing = []
        if profile_genres:
            catalog_genres = set(genre_counts.keys())
            missing = [g for g in profile_genres if g not in catalog_genres]
        return CoverageResult(genre_counts=genre_counts, total_songs=total,
                              coverage_scores=coverage_scores, underrepresented=underrepresented,
                              missing_from_catalog=missing)

    def genre_lockout(self, profile_name: str, user_prefs: Dict, songs: List[Dict]) -> LockoutResult:
        requested = user_prefs.get("favorite_genre", "")
        matching = [s for s in songs if s.get("genre") == requested]
        count = len(matching)
        lockout = count == 0
        if lockout:
            msg = f"LOCKOUT: Genre '{requested}' has zero songs in catalog."
        elif count == 1:
            msg = f"WARNING: Genre '{requested}' has only 1 song."
        else:
            msg = f"OK: Genre '{requested}' has {count} songs in catalog."
        return LockoutResult(profile_name=profile_name, requested_genre=requested,
                             genre_in_catalog=count > 0, songs_in_genre=count,
                             lockout_detected=lockout, message=msg)

    def score_distribution(self, profile_name: str, results: List[Tuple]) -> DistributionResult:
        if not results:
            return DistributionResult(profile_name=profile_name, top_score=0, second_score=0,
                                      mean_score=0, score_gap=0, dominance_ratio=0,
                                      is_dominant=False, message="No results to analyze.")
        scores = [score for _, score, _ in results]
        top = scores[0]
        second = scores[1] if len(scores) > 1 else 0.0
        mean = sum(scores) / len(scores)
        gap = top - second
        ratio = top / mean if mean > 0 else 0.0
        dominant = gap > 2.0 or ratio > 2.5
        if dominant:
            msg = f"DOMINANT: #1 scores {top:.2f}, #2 scores {second:.2f} (gap={gap:.2f})."
        else:
            msg = f"OK: Scores are well-distributed (gap={gap:.2f}, ratio={ratio:.2f})."
        return DistributionResult(profile_name=profile_name, top_score=top, second_score=second,
                                  mean_score=round(mean, 2), score_gap=round(gap, 2),
                                  dominance_ratio=round(ratio, 2), is_dominant=dominant, message=msg)

    def detect_contradictions(self, profile_name: str, user_prefs: Dict,
                              genre_context=None) -> ContradictionResult:
        contradictions: List[str] = []
        target_energy = user_prefs.get("target_energy", 0.5)
        likes_acoustic = user_prefs.get("likes_acoustic", False)
        genre = user_prefs.get("favorite_genre", "")
        mood = user_prefs.get("favorite_mood", "")

        if genre_context and hasattr(genre_context, "typical_energy"):
            lo, hi = genre_context.typical_energy
            if target_energy < lo - 0.15 or target_energy > hi + 0.15:
                contradictions.append(
                    f"Energy target {target_energy:.2f} is outside typical range "
                    f"[{lo:.1f}-{hi:.1f}] for genre '{genre}'")

        if likes_acoustic and target_energy > 0.8:
            contradictions.append(
                f"Acoustic preference + high energy ({target_energy:.2f}) is unusual")

        high_e_moods = {"energetic", "intense", "angry"}
        low_e_moods = {"chill", "relaxed", "sad", "melancholic"}
        if mood in high_e_moods and target_energy < 0.3:
            contradictions.append(f"Mood '{mood}' suggests high energy but target is {target_energy:.2f}")
        if mood in low_e_moods and target_energy > 0.85:
            contradictions.append(f"Mood '{mood}' suggests low energy but target is {target_energy:.2f}")

        if not contradictions:
            severity, msg = "none", "No contradictions detected."
        elif len(contradictions) >= 2:
            severity, msg = "severe", f"SEVERE: {len(contradictions)} contradictions found."
        else:
            severity, msg = "mild", f"MILD: {len(contradictions)} contradiction found."

        return ContradictionResult(profile_name=profile_name, contradictions=contradictions,
                                   severity=severity, message=msg)

    def diversity_index(self, profile_name: str, results: List[Tuple]) -> DiversityResult:
        if not results:
            return DiversityResult(profile_name=profile_name, genre_distribution={},
                                   shannon_entropy=0, max_possible_entropy=0,
                                   normalized_diversity=0, message="No results.")
        genre_dist: Dict[str, int] = {}
        for song, _, _ in results:
            g = song.get("genre", "unknown")
            genre_dist[g] = genre_dist.get(g, 0) + 1
        total = len(results)
        entropy = 0.0
        for count in genre_dist.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        max_entropy = math.log2(total) if total > 1 else 1.0
        normalized = entropy / max_entropy if max_entropy > 0 else 0.0

        if normalized >= 0.8:
            msg = f"HIGH diversity: {len(genre_dist)} genres in {total} results"
        elif normalized >= 0.5:
            msg = f"MODERATE diversity: {len(genre_dist)} genres in {total} results"
        else:
            msg = f"LOW diversity: {len(genre_dist)} genres dominate {total} results"

        return DiversityResult(profile_name=profile_name, genre_distribution=genre_dist,
                               shannon_entropy=round(entropy, 3),
                               max_possible_entropy=round(max_entropy, 3),
                               normalized_diversity=round(normalized, 3), message=msg)

    def fairness_report(self, profiles: Dict[str, Dict], songs: List[Dict],
                        results_by_profile: Dict[str, List[Tuple]],
                        genre_contexts=None) -> FairnessReport:
        profile_genres = [p.get("favorite_genre", "") for p in profiles.values()]
        coverage = self.genre_coverage(songs, profile_genres)
        lockouts, distributions, contradictions, diversities = [], [], [], []

        for name, prefs in profiles.items():
            lockouts.append(self.genre_lockout(name, prefs, songs))
            results = results_by_profile.get(name, [])
            distributions.append(self.score_distribution(name, results))
            diversities.append(self.diversity_index(name, results))
            ctx = (genre_contexts or {}).get(name)
            contradictions.append(self.detect_contradictions(name, prefs, ctx))

        penalties, total_checks = 0.0, 0
        for lo in lockouts:
            total_checks += 1
            if lo.lockout_detected:
                penalties += 1.0
        for div in diversities:
            total_checks += 1
            if div.normalized_diversity < 0.5:
                penalties += 0.5
        for dist in distributions:
            total_checks += 1
            if dist.is_dominant:
                penalties += 0.5
        for con in contradictions:
            total_checks += 1
            if con.severity == "severe":
                penalties += 0.3

        overall = max(0.0, 1.0 - (penalties / max(total_checks, 1)))
        summary = "\n".join([
            f"Fairness Score: {overall:.2f}/1.00",
            f"Profiles analyzed: {len(profiles)}",
            f"Genre lockouts: {sum(1 for l in lockouts if l.lockout_detected)}",
            f"Dominant distributions: {sum(1 for d in distributions if d.is_dominant)}",
            f"Low diversity: {sum(1 for d in diversities if d.normalized_diversity < 0.5)}",
            f"Contradictions: {sum(1 for c in contradictions if c.severity != 'none')}",
        ])

        return FairnessReport(coverage=coverage, lockouts=lockouts, distributions=distributions,
                              contradictions=contradictions, diversities=diversities,
                              overall_score=round(overall, 2), summary=summary)
