"""
Core recommendation logic for the Music Recommender Simulation.

Provides two parallel APIs:
  - Functional (dict-based): load_songs / score_song / recommend_songs  — used by main.py
  - OOP (dataclass-based):   Song / UserProfile / Recommender           — used by tests

Optional challenges implemented here:
  Challenge 1 — Advanced features: popularity, release_decade, mood_tags
  Challenge 2 — Scoring modes:     SCORING_MODES dict + ScoringWeights
  Challenge 3 — Diversity filter:  apply_diversity_filter()
"""

import csv
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Song:
    """Represents a song and its audio/metadata attributes."""
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float
    # Challenge 1: advanced features (default values keep existing tests passing)
    popularity: int = 50
    release_decade: str = "2020s"
    mood_tags: str = ""  # comma-separated string, e.g. "cozy,late-night,focused"

    def tags(self) -> List[str]:
        """Return mood_tags as a parsed list."""
        return [t.strip() for t in self.mood_tags.split(",") if t.strip()]


@dataclass
class UserProfile:
    """Represents a listener's taste preferences used to score songs."""
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool
    # Challenge 1: optional advanced preferences
    target_popularity: Optional[float] = None   # 0–100, or None to skip
    preferred_decade: Optional[str] = None      # e.g. "2020s", or None to skip
    liked_tags: Optional[List[str]] = None      # e.g. ["cozy", "studious"]


# ---------------------------------------------------------------------------
# Challenge 2: Scoring modes — Strategy pattern
# ---------------------------------------------------------------------------

@dataclass
class ScoringWeights:
    """
    Weight multipliers for each scoring signal.
    Changing a mode is just choosing a different ScoringWeights instance.
    """
    genre: float = 2.0      # exact genre match bonus
    mood: float = 1.5       # exact mood match bonus
    energy: float = 1.5     # multiplied by energy closeness (0–1)
    acoustic: float = 1.0   # acoustic bonus when likes_acoustic=True
    popularity: float = 0.5 # multiplied by popularity closeness (0–1)
    decade: float = 0.5     # exact decade match bonus
    tag: float = 0.3        # per matched mood tag


SCORING_MODES: Dict[str, ScoringWeights] = {
    # Default: balanced across all signals
    "balanced":       ScoringWeights(),
    # Genre is the dominant signal; other weights are halved
    "genre_first":    ScoringWeights(genre=4.0, mood=0.75, energy=0.75, acoustic=0.5),
    # Mood is the dominant signal; genre is secondary
    "mood_first":     ScoringWeights(genre=1.0, mood=3.0,  energy=0.75, acoustic=0.5),
    # Energy proximity dominates; genre/mood are tie-breakers only
    "energy_focused": ScoringWeights(genre=1.0, mood=0.75, energy=3.0,  acoustic=0.75),
}


# ---------------------------------------------------------------------------
# OOP class — used by tests/test_recommender.py
# ---------------------------------------------------------------------------

class Recommender:
    """OOP wrapper; operates on Song / UserProfile dataclass objects."""

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def _score(
        self, user: UserProfile, song: Song, weights: ScoringWeights = None
    ) -> Tuple[float, List[str]]:
        """Score a Song dataclass against a UserProfile; return (score, reasons)."""
        if weights is None:
            weights = SCORING_MODES["balanced"]

        score = 0.0
        reasons: List[str] = []

        if song.genre == user.favorite_genre:
            score += weights.genre
            reasons.append(f"genre match: {song.genre} (+{weights.genre})")

        if song.mood == user.favorite_mood:
            score += weights.mood
            reasons.append(f"mood match: {song.mood} (+{weights.mood})")

        energy_closeness = 1.0 - abs(user.target_energy - song.energy)
        energy_pts = round(weights.energy * energy_closeness, 2)
        score += energy_pts
        reasons.append(
            f"energy proximity: {song.energy:.2f} vs target {user.target_energy:.2f} (+{energy_pts})"
        )

        if user.likes_acoustic and song.acousticness > 0.6:
            score += weights.acoustic
            reasons.append(f"acoustic match: {song.acousticness:.2f} (+{weights.acoustic})")

        # Challenge 1: advanced features
        if user.target_popularity is not None:
            pop_closeness = 1.0 - abs(user.target_popularity - song.popularity) / 100
            pop_pts = round(weights.popularity * pop_closeness, 2)
            score += pop_pts
            reasons.append(
                f"popularity: {song.popularity} vs target {int(user.target_popularity)} (+{pop_pts})"
            )

        if user.preferred_decade and song.release_decade == user.preferred_decade:
            score += weights.decade
            reasons.append(f"decade match: {song.release_decade} (+{weights.decade})")

        if user.liked_tags:
            song_tag_list = song.tags()
            matched = [t for t in user.liked_tags if t in song_tag_list]
            if matched:
                tag_pts = round(len(matched) * weights.tag, 2)
                score += tag_pts
                reasons.append(f"tag matches: {', '.join(matched)} (+{tag_pts})")

        return round(score, 2), reasons

    def recommend(
        self, user: UserProfile, k: int = 5, mode: str = "balanced"
    ) -> List[Song]:
        """Return the top k Song objects ranked by score, highest first."""
        weights = SCORING_MODES.get(mode, SCORING_MODES["balanced"])
        scored = [(song, self._score(user, song, weights)[0]) for song in self.songs]
        return [song for song, _ in sorted(scored, key=lambda x: x[1], reverse=True)[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a human-readable explanation for why a song was recommended."""
        _, reasons = self._score(user, song)
        return "; ".join(reasons) if reasons else "No strong match found."


# ---------------------------------------------------------------------------
# Functional API (dict-based) — used by src/main.py
# ---------------------------------------------------------------------------

def load_songs(csv_path: str) -> List[Dict]:
    """Read songs.csv and return a list of dicts with numeric fields cast to correct types."""
    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw_tags = row.get("mood_tags", "")
            songs.append({
                "id":             int(row["id"]),
                "title":          row["title"],
                "artist":         row["artist"],
                "genre":          row["genre"],
                "mood":           row["mood"],
                "energy":         float(row["energy"]),
                "tempo_bpm":      float(row["tempo_bpm"]),
                "valence":        float(row["valence"]),
                "danceability":   float(row["danceability"]),
                "acousticness":   float(row["acousticness"]),
                # Challenge 1 fields
                "popularity":     int(row.get("popularity", 50)),
                "release_decade": row.get("release_decade", "2020s"),
                "mood_tags":      [t.strip() for t in raw_tags.split(",") if t.strip()],
            })
    return songs


def score_song(
    user_prefs: Dict,
    song: Dict,
    weights: ScoringWeights = None,
) -> Tuple[float, List[str]]:
    """
    Score one song dict against user preference dict.

    Scoring recipe (balanced mode, max ~6.0 base points + optional advanced bonuses):
      +2.0  exact genre match
      +1.5  exact mood match
      +0–1.5  energy proximity  = 1.5 × (1 − |target_energy − song_energy|)
      +1.0  acoustic bonus when likes_acoustic=True and acousticness > 0.6
      +0–0.5  popularity proximity  (Challenge 1, optional)
      +0.5  exact decade match      (Challenge 1, optional)
      +0.3  per matched mood tag    (Challenge 1, optional)

    Returns:
        (score, reasons) where reasons is a list of human-readable strings.
    """
    if weights is None:
        weights = SCORING_MODES["balanced"]

    score = 0.0
    reasons: List[str] = []

    if song["genre"] == user_prefs.get("favorite_genre", ""):
        score += weights.genre
        reasons.append(f"genre match: {song['genre']} (+{weights.genre})")

    if song["mood"] == user_prefs.get("favorite_mood", ""):
        score += weights.mood
        reasons.append(f"mood match: {song['mood']} (+{weights.mood})")

    target = user_prefs.get("target_energy", 0.5)
    energy_closeness = 1.0 - abs(target - song["energy"])
    energy_pts = round(weights.energy * energy_closeness, 2)
    score += energy_pts
    reasons.append(
        f"energy proximity: {song['energy']:.2f} vs target {target:.2f} (+{energy_pts})"
    )

    if user_prefs.get("likes_acoustic", False) and song["acousticness"] > 0.6:
        score += weights.acoustic
        reasons.append(f"acoustic match: {song['acousticness']:.2f} (+{weights.acoustic})")

    # Challenge 1: advanced optional features
    target_pop = user_prefs.get("target_popularity")
    if target_pop is not None:
        pop_closeness = 1.0 - abs(target_pop - song["popularity"]) / 100
        pop_pts = round(weights.popularity * pop_closeness, 2)
        score += pop_pts
        reasons.append(
            f"popularity: {song['popularity']} vs target {int(target_pop)} (+{pop_pts})"
        )

    pref_decade = user_prefs.get("preferred_decade")
    if pref_decade and song.get("release_decade") == pref_decade:
        score += weights.decade
        reasons.append(f"decade match: {song['release_decade']} (+{weights.decade})")

    liked_tags = user_prefs.get("liked_tags") or []
    song_tags = song.get("mood_tags") or []
    if liked_tags and song_tags:
        matched = [t for t in liked_tags if t in song_tags]
        if matched:
            tag_pts = round(len(matched) * weights.tag, 2)
            score += tag_pts
            reasons.append(f"tag matches: {', '.join(matched)} (+{tag_pts})")

    return round(score, 2), reasons


def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    mode: str = "balanced",
) -> List[Tuple[Dict, float, str]]:
    """
    Score every song, sort by score descending, return the top k results.

    Uses sorted() (non-mutating) so the original catalog list is never
    modified — the same songs list can be reused for multiple profiles
    and modes without reloading the CSV.

    Returns:
        List of (song_dict, score, explanation_string) tuples.
    """
    weights = SCORING_MODES.get(mode, SCORING_MODES["balanced"])
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song, weights)
        scored.append((song, score, " | ".join(reasons)))
    return sorted(scored, key=lambda x: x[1], reverse=True)[:k]


def apply_diversity_filter(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    max_per_genre: int = 2,
    max_per_artist: int = 1,
    mode: str = "balanced",
) -> List[Tuple[Dict, float, str]]:
    """
    Challenge 3: Score the full catalog, then walk the ranked list and
    skip any song that would exceed max_per_genre or max_per_artist.

    This enforces diversity without changing the scoring formula — it is
    a post-processing step applied to the already-ranked results.

    Returns:
        List of (song_dict, score, explanation_string) tuples, length <= k.
    """
    weights = SCORING_MODES.get(mode, SCORING_MODES["balanced"])

    # Score and rank the full catalog
    full_ranked = []
    for song in songs:
        score, reasons = score_song(user_prefs, song, weights)
        full_ranked.append((song, score, " | ".join(reasons)))
    full_ranked.sort(key=lambda x: x[1], reverse=True)

    genre_count: Dict[str, int] = {}
    artist_count: Dict[str, int] = {}
    diverse: List[Tuple[Dict, float, str]] = []

    for song, score, explanation in full_ranked:
        if len(diverse) >= k:
            break
        g = song["genre"]
        a = song["artist"]
        if genre_count.get(g, 0) >= max_per_genre:
            continue
        if artist_count.get(a, 0) >= max_per_artist:
            continue
        diverse.append((song, score, explanation))
        genre_count[g] = genre_count.get(g, 0) + 1
        artist_count[a] = artist_count.get(a, 0) + 1

    return diverse
