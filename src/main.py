"""
Command-line runner for the Music Recommender Simulation.

Run from the project root with:
    python -m src.main

Showcases all four optional challenges:
  Challenge 1 — Advanced features  : popularity, release_decade, mood_tags
  Challenge 2 — Scoring modes      : balanced / genre_first / mood_first / energy_focused
  Challenge 3 — Diversity filter   : limits same-genre and same-artist repeats
  Challenge 4 — Visual table       : tabulate for clean terminal output
"""

from src.recommender import (
    load_songs,
    recommend_songs,
    apply_diversity_filter,
    SCORING_MODES,
)

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False


# ---------------------------------------------------------------------------
# User profiles
# ---------------------------------------------------------------------------

PROFILES = {
    "High-Energy Pop Fan": {
        "favorite_genre": "pop",
        "favorite_mood":  "happy",
        "target_energy":  0.85,
        "likes_acoustic": False,
    },
    "Chill Lofi Student": {
        "favorite_genre":    "lofi",
        "favorite_mood":     "chill",
        "target_energy":     0.40,
        "likes_acoustic":    True,
        # Challenge 1: advanced preferences
        "target_popularity": 65,
        "preferred_decade":  "2020s",
        "liked_tags":        ["cozy", "studious", "late-night"],
    },
    "Deep Intense Rock": {
        "favorite_genre": "rock",
        "favorite_mood":  "intense",
        "target_energy":  0.91,
        "likes_acoustic": False,
    },
}


# ---------------------------------------------------------------------------
# Display helpers (Challenge 4: tabulate)
# ---------------------------------------------------------------------------

def _bar(title: str, width: int = 70) -> None:
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


def _profile_line(prefs: dict) -> str:
    base = (
        f"genre={prefs['favorite_genre']} | mood={prefs['favorite_mood']} | "
        f"energy={prefs['target_energy']} | acoustic={prefs['likes_acoustic']}"
    )
    extras = []
    if prefs.get("target_popularity") is not None:
        extras.append(f"popularity~{prefs['target_popularity']}")
    if prefs.get("preferred_decade"):
        extras.append(f"decade={prefs['preferred_decade']}")
    if prefs.get("liked_tags"):
        extras.append(f"tags={prefs['liked_tags']}")
    return base + ("  |  " + "  |  ".join(extras) if extras else "")


def print_results(
    label: str,
    prefs: dict,
    results: list,
    note: str = "",
    full_reasons: bool = False,
) -> None:
    """Print a recommendation block using tabulate when available."""
    _bar(label)
    print(f"  {_profile_line(prefs)}")
    if note:
        print(f"  [{note}]")

    rows = []
    for rank, (song, score, explanation) in enumerate(results, 1):
        reason_list = explanation.split(" | ")
        rows.append([
            f"#{rank}",
            song["title"],
            song["artist"],
            f"{score:.2f}",
            reason_list[0],   # top signal for table view
        ])

    print()
    if HAS_TABULATE:
        print(tabulate(rows, headers=["", "Title", "Artist", "Score", "Top Signal"],
                       tablefmt="simple"))
    else:
        for r in rows:
            print(f"  {r[0]:3}  {r[1]:<28}  {r[3]:6}  {r[4]}")

    if full_reasons:
        print()
        for rank, (song, score, explanation) in enumerate(results, 1):
            print(f"  #{rank} {song['title']} — full breakdown:")
            for reason in explanation.split(" | "):
                print(f"       - {reason}")
    print()


def print_mode_comparison(label: str, prefs: dict, songs: list) -> None:
    """Challenge 2: show #1 and #2 for every scoring mode side-by-side."""
    _bar(f"Mode Comparison — {label}")
    print(f"  {_profile_line(prefs)}\n")

    rows = []
    for mode_name, weights in SCORING_MODES.items():
        top2 = recommend_songs(prefs, songs, k=2, mode=mode_name)
        s1, sc1 = (top2[0][0]["title"], top2[0][1]) if top2 else ("-", 0)
        s2, sc2 = (top2[1][0]["title"], top2[1][1]) if len(top2) > 1 else ("-", 0)
        max_score = weights.genre + weights.mood + weights.energy + weights.acoustic
        rows.append([mode_name, s1, f"{sc1:.2f}", s2, f"{sc2:.2f}", f"~{max_score:.1f}"])

    if HAS_TABULATE:
        print(tabulate(rows,
                       headers=["Mode", "#1 Song", "Score", "#2 Song", "Score", "Max pts"],
                       tablefmt="simple"))
    else:
        for r in rows:
            print(f"  {r[0]:15}  #1: {r[1]} ({r[2]})  #2: {r[3]} ({r[4]})")
    print()


def print_diversity_demo(label: str, prefs: dict, songs: list, k: int = 5) -> None:
    """Challenge 3: show before / after applying the diversity filter."""
    before = recommend_songs(prefs, songs, k=k)
    after  = apply_diversity_filter(prefs, songs, k=k, max_per_genre=2, max_per_artist=1)

    _bar(f"Diversity Filter — {label}")
    print(f"  {_profile_line(prefs)}\n")

    def to_rows(results):
        return [
            [f"#{i+1}", s["title"], s["genre"], s["artist"], f"{sc:.2f}"]
            for i, (s, sc, _) in enumerate(results)
        ]

    hdrs = ["", "Title", "Genre", "Artist", "Score"]
    if HAS_TABULATE:
        print("  BEFORE (no diversity filter):")
        print(tabulate(to_rows(before), headers=hdrs, tablefmt="simple"))
        print("\n  AFTER  (max 2 per genre, max 1 per artist):")
        print(tabulate(to_rows(after), headers=hdrs, tablefmt="simple"))
    else:
        print("  BEFORE:")
        for r in to_rows(before):
            print(f"    {r[0]}  {r[1]} [{r[2]}] by {r[3]}  {r[4]}")
        print("  AFTER:")
        for r in to_rows(after):
            print(f"    {r[0]}  {r[1]} [{r[2]}] by {r[3]}  {r[4]}")

    # Highlight what changed
    before_titles = {s["title"] for s, _, _ in before}
    after_titles  = {s["title"] for s, _, _ in after}
    removed = before_titles - after_titles
    added   = after_titles  - before_titles
    print()
    if removed:
        print(f"  Removed (diversity rule): {', '.join(sorted(removed))}")
        print(f"  Replaced with:            {', '.join(sorted(added))}")
    else:
        print("  No changes — results were already diverse.")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded {len(songs)} songs.\n")

    if not HAS_TABULATE:
        print("  [tip: run  pip install tabulate  for a prettier table]\n")

    # ── Challenge 1 + 4: Advanced features with tabulate ──────────────────
    print("=" * 70)
    print("  CHALLENGE 1 + 4: Advanced Features & Visual Table")
    print("=" * 70)

    lofi = PROFILES["Chill Lofi Student"]
    results = recommend_songs(lofi, songs, k=5, mode="balanced")
    print_results(
        "Chill Lofi Student — balanced mode with advanced prefs",
        lofi,
        results,
        note="popularity + decade + mood-tag scoring active",
        full_reasons=True,
    )

    # ── Challenge 2: Scoring modes ─────────────────────────────────────────
    print("=" * 70)
    print("  CHALLENGE 2: Multiple Scoring Modes")
    print("=" * 70)

    for label, prefs in PROFILES.items():
        print_mode_comparison(label, prefs, songs)

    # ── Challenge 3: Diversity filter ─────────────────────────────────────
    print("=" * 70)
    print("  CHALLENGE 3: Diversity Filter")
    print("=" * 70)

    print_diversity_demo("Chill Lofi Student", lofi, songs)
    print_diversity_demo("High-Energy Pop Fan", PROFILES["High-Energy Pop Fan"], songs)


if __name__ == "__main__":
    main()
