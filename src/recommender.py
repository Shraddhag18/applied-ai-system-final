"""
Core recommendation logic for the Music Recommender Simulation.

Provides two parallel APIs:
  - Functional (dict-based): load_songs / score_song / recommend_songs  — used by main.py
  - OOP (dataclass-based):   Song / UserProfile / Recommender           — used by tests
"""

import csv
from dataclasses import dataclass
from typing import Dict, List, Tuple


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


@dataclass
class UserProfile:
    """Represents a listener's taste preferences used to score songs."""
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


class Recommender:
    """OOP wrapper around the scoring logic; operates on Song / UserProfile objects."""

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def _score(self, user: UserProfile, song: Song) -> Tuple[float, List[str]]:
        """Score a Song dataclass against a UserProfile; return (score, reasons)."""
        score = 0.0
        reasons: List[str] = []

        if song.genre == user.favorite_genre:
            score += 2.0
            reasons.append(f"genre match: {song.genre} (+2.0)")

        if song.mood == user.favorite_mood:
            score += 1.5
            reasons.append(f"mood match: {song.mood} (+1.5)")

        energy_closeness = 1.0 - abs(user.target_energy - song.energy)
        energy_pts = round(1.5 * energy_closeness, 2)
        score += energy_pts
        reasons.append(
            f"energy proximity: {song.energy:.2f} vs target {user.target_energy:.2f} (+{energy_pts})"
        )

        if user.likes_acoustic and song.acousticness > 0.6:
            score += 1.0
            reasons.append(f"acoustic match: acousticness={song.acousticness:.2f} (+1.0)")

        return round(score, 2), reasons

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top k Song objects ranked by score, highest first."""
        scored = [(song, self._score(user, song)[0]) for song in self.songs]
        return [song for song, _ in sorted(scored, key=lambda x: x[1], reverse=True)[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a human-readable explanation for why a song was recommended."""
        _, reasons = self._score(user, song)
        return "; ".join(reasons) if reasons else "No strong match found."


# ---------------------------------------------------------------------------
# Functional API (dict-based) — used by src/main.py
# ---------------------------------------------------------------------------

def load_songs(csv_path: str) -> List[Dict]:
    """Read songs.csv and return a list of dicts with numeric fields cast to float/int."""
    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            songs.append({
                "id":           int(row["id"]),
                "title":        row["title"],
                "artist":       row["artist"],
                "genre":        row["genre"],
                "mood":         row["mood"],
                "energy":       float(row["energy"]),
                "tempo_bpm":    float(row["tempo_bpm"]),
                "valence":      float(row["valence"]),
                "danceability": float(row["danceability"]),
                "acousticness": float(row["acousticness"]),
            })
    return songs


def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    Score one song dict against user preference dict.

    Scoring recipe (max 6.0 points):
      +2.0  exact genre match
      +1.5  exact mood match
      +0–1.5  energy proximity  = 1.5 × (1 − |target_energy − song_energy|)
      +1.0  acoustic bonus when likes_acoustic=True and acousticness > 0.6

    Returns:
        (score, reasons) where reasons is a list of human-readable strings.
    """
    score = 0.0
    reasons: List[str] = []

    if song["genre"] == user_prefs.get("favorite_genre", ""):
        score += 2.0
        reasons.append(f"genre match: {song['genre']} (+2.0)")

    if song["mood"] == user_prefs.get("favorite_mood", ""):
        score += 1.5
        reasons.append(f"mood match: {song['mood']} (+1.5)")

    target = user_prefs.get("target_energy", 0.5)
    energy_closeness = 1.0 - abs(target - song["energy"])
    energy_pts = round(1.5 * energy_closeness, 2)
    score += energy_pts
    reasons.append(
        f"energy proximity: {song['energy']:.2f} vs target {target:.2f} (+{energy_pts})"
    )

    if user_prefs.get("likes_acoustic", False) and song["acousticness"] > 0.6:
        score += 1.0
        reasons.append(f"acoustic match: acousticness={song['acousticness']:.2f} (+1.0)")

    return round(score, 2), reasons


def recommend_songs(
    user_prefs: Dict, songs: List[Dict], k: int = 5
) -> List[Tuple[Dict, float, str]]:
    """
    Score every song, sort by score descending, return the top k results.

    Uses sorted() (non-mutating) rather than list.sort() so the original
    catalog list is never modified — callers can reuse it for a different
    user profile without reloading the CSV.

    Returns:
        List of (song_dict, score, explanation_string) tuples.
    """
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        explanation = " | ".join(reasons)
        scored.append((song, score, explanation))

    return sorted(scored, key=lambda x: x[1], reverse=True)[:k]
