"""
Command-line runner for the Music Recommender Simulation.

Run from the project root with:
    python -m src.main
"""

from src.recommender import load_songs, recommend_songs, score_song


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

PROFILES = {
    "High-Energy Pop Fan": {
        "favorite_genre": "pop",
        "favorite_mood":  "happy",
        "target_energy":  0.85,
        "likes_acoustic": False,
    },
    "Chill Lofi Student": {
        "favorite_genre": "lofi",
        "favorite_mood":  "chill",
        "target_energy":  0.40,
        "likes_acoustic": True,
    },
    "Deep Intense Rock": {
        "favorite_genre": "rock",
        "favorite_mood":  "intense",
        "target_energy":  0.91,
        "likes_acoustic": False,
    },
    # --- adversarial / edge-case profiles ---
    "Conflicted (high energy + sad + acoustic)": {
        "favorite_genre": "classical",
        "favorite_mood":  "sad",
        "target_energy":  0.90,   # wants high energy but sad classical
        "likes_acoustic": True,
    },
    "Unknown Genre (k-pop not in catalog)": {
        "favorite_genre": "k-pop",
        "favorite_mood":  "happy",
        "target_energy":  0.80,
        "likes_acoustic": False,
    },
    "Perfectly Middle (jazz / relaxed / 0.5 energy)": {
        "favorite_genre": "jazz",
        "favorite_mood":  "relaxed",
        "target_energy":  0.50,
        "likes_acoustic": True,
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def print_recommendations(label: str, user_prefs: dict, results: list) -> None:
    """Print a formatted block of recommendations for one profile."""
    bar = "=" * 60
    print(f"\n{bar}")
    print(f"  Profile: {label}")
    print(
        f"  genre={user_prefs['favorite_genre']} | "
        f"mood={user_prefs['favorite_mood']} | "
        f"energy={user_prefs['target_energy']} | "
        f"acoustic={user_prefs['likes_acoustic']}"
    )
    print(bar)
    for rank, (song, score, explanation) in enumerate(results, start=1):
        print(f"\n  #{rank}  {song['title']}  by  {song['artist']}")
        print(f"       Score : {score:.2f} / 6.00")
        for reason in explanation.split(" | "):
            print(f"       - {reason}")
    print()


def run_weight_experiment(songs: list) -> None:
    """
    Experiment: double energy weight (3.0), halve genre weight (1.0).
    Uses a custom scorer inline so recommender.py weights are unchanged.
    """
    user_prefs = PROFILES["High-Energy Pop Fan"]

    def experimental_score(prefs, song):
        score = 0.0
        reasons = []
        if song["genre"] == prefs.get("favorite_genre", ""):
            score += 1.0                        # halved from 2.0
            reasons.append(f"genre match: {song['genre']} (+1.0)")
        if song["mood"] == prefs.get("favorite_mood", ""):
            score += 1.5
            reasons.append(f"mood match: {song['mood']} (+1.5)")
        target = prefs.get("target_energy", 0.5)
        closeness = 1.0 - abs(target - song["energy"])
        pts = round(3.0 * closeness, 2)         # doubled from 1.5
        score += pts
        reasons.append(f"energy proximity: {song['energy']:.2f} vs target {target:.2f} (+{pts})")
        if prefs.get("likes_acoustic", False) and song["acousticness"] > 0.6:
            score += 1.0
            reasons.append(f"acoustic match: acousticness={song['acousticness']:.2f} (+1.0)")
        return round(score, 2), reasons

    scored = []
    for song in songs:
        score, reasons = experimental_score(user_prefs, song)
        scored.append((song, score, " | ".join(reasons)))
    top5 = sorted(scored, key=lambda x: x[1], reverse=True)[:5]

    bar = "=" * 60
    print(f"\n{bar}")
    print("  EXPERIMENT: Genre x0.5 (+1.0)  |  Energy x2.0 (+3.0)")
    print("  Profile: High-Energy Pop Fan (same as above)")
    print(bar)
    for rank, (song, score, explanation) in enumerate(top5, start=1):
        print(f"\n  #{rank}  {song['title']}  by  {song['artist']}")
        print(f"       Score : {score:.2f} / 6.50 (new max)")
        for reason in explanation.split(" | "):
            print(f"       - {reason}")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded {len(songs)} songs.\n")

    for label, prefs in PROFILES.items():
        results = recommend_songs(prefs, songs, k=5)
        print_recommendations(label, prefs, results)

    print("\n--- Weight Sensitivity Experiment ---")
    run_weight_experiment(songs)


if __name__ == "__main__":
    main()
