"""
Command-line runner for the Music Recommender Simulation.

Run from the project root with:
    python -m src.main
"""

from src.recommender import load_songs, recommend_songs


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded {len(songs)} songs.\n")

    # User taste profile — drives all scoring decisions
    # favorite_genre / favorite_mood: exact-match categorical signals
    # target_energy: 0.0 (silent) to 1.0 (maximum intensity)
    # likes_acoustic: True gives a bonus to songs with acousticness > 0.6
    user_prefs = {
        "favorite_genre": "lofi",
        "favorite_mood": "chill",
        "target_energy": 0.40,
        "likes_acoustic": True,
    }

    recommendations = recommend_songs(user_prefs, songs, k=5)

    print("=" * 56)
    print("  Top Recommendations")
    print(
        f"  Profile: genre={user_prefs['favorite_genre']} | "
        f"mood={user_prefs['favorite_mood']} | "
        f"energy={user_prefs['target_energy']} | "
        f"acoustic={user_prefs['likes_acoustic']}"
    )
    print("=" * 56)

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n#{rank}  {song['title']}  by  {song['artist']}")
        print(f"     Score : {score:.2f} / 6.00")
        for reason in explanation.split(" | "):
            print(f"     - {reason}")

    print()


if __name__ == "__main__":
    main()
