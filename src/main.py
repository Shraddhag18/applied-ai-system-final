"""
VibeFinder 2.0 — Applied AI Music Recommendation System.

Command-line runner that demonstrates all AI components:
  1. Original v1.0 baseline recommendations
  2. Agentic workflow with step-by-step reasoning log
  3. Bias detection and fairness report
  4. Guardrail demonstrations
  5. Confidence scoring and self-critique
  6. Reliability experiment summary

Run from the project root:
    python -m src.main
"""

from src.recommender import (
    load_songs, recommend_songs, apply_diversity_filter,
    score_song, SCORING_MODES, ScoringWeights,
)
from src.retrieval import KnowledgeBase
from src.agent import RecommendationAgent
from src.bias_detector import BiasDetector
from src.guardrails import InputValidator, OutputGuardrail
from src.confidence import ConfidenceScorer

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
    "Conflicted (High Energy + Sad + Acoustic)": {
        "favorite_genre": "classical",
        "favorite_mood":  "sad",
        "target_energy":  0.90,
        "likes_acoustic": True,
    },
    "Unknown Genre (K-pop not in catalog)": {
        "favorite_genre": "k-pop",
        "favorite_mood":  "happy",
        "target_energy":  0.80,
        "likes_acoustic": False,
    },
    "Perfectly Middle (Jazz / Relaxed / 0.5)": {
        "favorite_genre": "jazz",
        "favorite_mood":  "relaxed",
        "target_energy":  0.50,
        "likes_acoustic": True,
    },
}


# ---------------------------------------------------------------------------
# Display helpers
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
    return base


def print_results(label, prefs, results, full_reasons=False):
    _bar(label)
    print(f"  {_profile_line(prefs)}")
    rows = []
    for rank, (song, score, explanation) in enumerate(results, 1):
        reason_list = explanation.split(" | ")
        rows.append([f"#{rank}", song["title"], song["artist"],
                      f"{score:.2f}", reason_list[0]])
    print()
    if HAS_TABULATE:
        print(tabulate(rows, headers=["", "Title", "Artist", "Score", "Top Signal"],
                       tablefmt="simple"))
    else:
        for r in rows:
            print(f"  {r[0]:3}  {r[1]:<28}  {r[3]:6}  {r[4]}")
    if full_reasons and results:
        print()
        song, score, explanation = results[0]
        print(f"  #{1} {song['title']} — full breakdown:")
        for reason in explanation.split(" | "):
            print(f"       - {reason}")
    print()


def print_mode_comparison(label, prefs, songs):
    _bar(f"Mode Comparison — {label}")
    rows = []
    for mode_name, weights in SCORING_MODES.items():
        top2 = recommend_songs(prefs, songs, k=2, mode=mode_name)
        s1, sc1 = (top2[0][0]["title"], top2[0][1]) if top2 else ("-", 0)
        s2, sc2 = (top2[1][0]["title"], top2[1][1]) if len(top2) > 1 else ("-", 0)
        max_score = weights.genre + weights.mood + weights.energy + weights.acoustic
        rows.append([mode_name, s1, f"{sc1:.2f}", s2, f"{sc2:.2f}", f"~{max_score:.1f}"])
    if HAS_TABULATE:
        print(tabulate(rows, headers=["Mode", "#1 Song", "Score", "#2 Song", "Score", "Max pts"],
                       tablefmt="simple"))
    else:
        for r in rows:
            print(f"  {r[0]:15}  #1: {r[1]} ({r[2]})  #2: {r[3]} ({r[4]})")
    print()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded {len(songs)} songs.\n")

    kb = KnowledgeBase("data/knowledge_base")
    agent = RecommendationAgent(songs, kb)
    bias_detector = BiasDetector()
    validator = InputValidator()
    confidence_scorer = ConfidenceScorer()

    # ══════════════════════════════════════════════════════════════════
    # SECTION 1: Original v1.0 Baseline Recommendations
    # ══════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  SECTION 1: Baseline Recommendations (v1.0 scoring)")
    print("=" * 70)

    for label, prefs in list(PROFILES.items())[:3]:
        results = recommend_songs(prefs, songs, k=5, mode="balanced")
        print_results(label, prefs, results, full_reasons=True)

    # ══════════════════════════════════════════════════════════════════
    # SECTION 2: Agentic Workflow Demo
    # ══════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  SECTION 2: Agentic Workflow — Step-by-Step Reasoning")
    print("=" * 70)

    demo_profiles = [
        ("Chill Lofi Student", PROFILES["Chill Lofi Student"]),
        ("Conflicted (High Energy + Sad + Acoustic)",
         PROFILES["Conflicted (High Energy + Sad + Acoustic)"]),
        ("Unknown Genre (K-pop not in catalog)",
         PROFILES["Unknown Genre (K-pop not in catalog)"]),
    ]

    for label, prefs in demo_profiles:
        _bar(f"Agent: {label}")
        result = agent.run(label, prefs)

        # Print step-by-step log
        for step in result.log.steps:
            print(f"  [{step.step.value.upper():8}] {step.decision}")

        print()
        if result.recommendations:
            top = result.recommendations[0]
            print(f"  Top pick: {top[0]['title']} (score: {top[1]:.2f})")
        print(f"  Confidence: {result.confidence.level} ({result.confidence.overall:.2f})")
        if result.confidence.critique:
            print(f"  Critique:")
            for c in result.confidence.critique:
                print(f"    - {c}")
        if result.warnings:
            print(f"  Warnings:")
            for w in result.warnings:
                print(f"    - {w}")
        print()

    # ══════════════════════════════════════════════════════════════════
    # SECTION 3: Bias Detection & Fairness Report
    # ══════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  SECTION 3: Bias Detection & Fairness Report")
    print("=" * 70)

    # Generate results for all profiles
    results_by_profile = {}
    for name, prefs in PROFILES.items():
        results_by_profile[name] = recommend_songs(prefs, songs, k=5)

    # Genre contexts from knowledge base
    genre_contexts = {}
    for name, prefs in PROFILES.items():
        ctx = kb.retrieve_context(prefs)
        if ctx.has_genre:
            genre_contexts[name] = ctx.genre_context

    report = bias_detector.fairness_report(PROFILES, songs, results_by_profile, genre_contexts)
    print(f"\n{report.summary}\n")

    # Coverage details
    print("  Genre Coverage:")
    for genre, count in sorted(report.coverage.genre_counts.items()):
        bar = "#" * count
        print(f"    {genre:12} {bar} ({count})")

    # Per-profile bias metrics
    print()
    if HAS_TABULATE:
        bias_rows = []
        for lo, div, con in zip(report.lockouts, report.diversities, report.contradictions):
            bias_rows.append([
                lo.profile_name[:30],
                "YES" if lo.lockout_detected else "no",
                f"{div.normalized_diversity:.2f}",
                con.severity,
            ])
        print(tabulate(bias_rows,
                       headers=["Profile", "Lockout?", "Diversity", "Contradictions"],
                       tablefmt="simple"))
    else:
        for lo, div, con in zip(report.lockouts, report.diversities, report.contradictions):
            print(f"  {lo.profile_name[:30]:32} lockout={lo.lockout_detected:5} "
                  f"diversity={div.normalized_diversity:.2f} contradictions={con.severity}")
    print()

    # ══════════════════════════════════════════════════════════════════
    # SECTION 4: Guardrail Demonstrations
    # ══════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  SECTION 4: Input Guardrails & Output Quality Checks")
    print("=" * 70)

    guardrail_tests = [
        ("Valid profile", {"favorite_genre": "pop", "favorite_mood": "happy",
                           "target_energy": 0.8, "likes_acoustic": False}),
        ("Missing genre", {"favorite_mood": "happy", "target_energy": 0.8}),
        ("Energy out of range", {"favorite_genre": "pop", "favorite_mood": "happy",
                                  "target_energy": 1.5}),
        ("Unknown mood", {"favorite_genre": "pop", "favorite_mood": "groovy",
                           "target_energy": 0.5}),
    ]

    for label, prefs in guardrail_tests:
        result = validator.validate(prefs)
        status = "PASS" if result.is_valid else "FAIL"
        detail = ""
        if result.errors:
            detail = f" — {result.errors[0]}"
        elif result.warnings:
            detail = f" — WARNING: {result.warnings[0]}"
        print(f"  [{status}] {label}{detail}")

    # Output guardrail demo
    print()
    guardrail = OutputGuardrail()
    catalog_genres = list({s["genre"] for s in songs})

    for label, prefs in [("Pop Fan", PROFILES["High-Energy Pop Fan"]),
                          ("K-pop Fan", PROFILES["Unknown Genre (K-pop not in catalog)"])]:
        results = recommend_songs(prefs, songs, k=5)
        check = guardrail.check(results, catalog_genres=catalog_genres,
                                user_genre=prefs["favorite_genre"])
        print(f"  Output check — {label}:")
        print(f"  {check.summary()}")
        print()

    # ══════════════════════════════════════════════════════════════════
    # SECTION 5: Confidence Scoring & Self-Critique
    # ══════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  SECTION 5: Confidence Scoring & Self-Critique")
    print("=" * 70)

    for label, prefs in PROFILES.items():
        results = recommend_songs(prefs, songs, k=5)
        ctx = kb.retrieve_context(prefs)
        genre_ctx = ctx.genre_context if ctx.has_genre else None
        conf = confidence_scorer.score_confidence(results, prefs, songs, genre_ctx)
        top_title = results[0][0]["title"] if results else "N/A"
        print(f"  {label[:40]:42} -> {conf.level:6} ({conf.overall:.2f})  "
              f"Top: {top_title}")

    # Detailed critique for adversarial profiles
    print()
    for label in ["Conflicted (High Energy + Sad + Acoustic)",
                   "Unknown Genre (K-pop not in catalog)"]:
        prefs = PROFILES[label]
        results = recommend_songs(prefs, songs, k=5)
        critique = confidence_scorer.self_critique(
            results, prefs, songs,
            kb.retrieve_context(prefs).genre_context)
        _bar(f"Self-Critique: {label}")
        print(f"  {critique.replace(chr(10), chr(10) + '  ')}")
        print()

    # ══════════════════════════════════════════════════════════════════
    # SECTION 6: Diversity Filter (preserved from v1.0)
    # ══════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  SECTION 6: Diversity Filter Demo")
    print("=" * 70)

    lofi = PROFILES["Chill Lofi Student"]
    before = recommend_songs(lofi, songs, k=5)
    after = apply_diversity_filter(lofi, songs, k=5, max_per_genre=2, max_per_artist=1)

    def to_rows(results):
        return [[f"#{i+1}", s["title"], s["genre"], s["artist"], f"{sc:.2f}"]
                for i, (s, sc, _) in enumerate(results)]

    hdrs = ["", "Title", "Genre", "Artist", "Score"]
    print("\n  BEFORE (no diversity filter):")
    if HAS_TABULATE:
        print(tabulate(to_rows(before), headers=hdrs, tablefmt="simple"))
    else:
        for r in to_rows(before):
            print(f"    {r[0]}  {r[1]} [{r[2]}] by {r[3]}  {r[4]}")

    print("\n  AFTER (max 2 per genre, max 1 per artist):")
    if HAS_TABULATE:
        print(tabulate(to_rows(after), headers=hdrs, tablefmt="simple"))
    else:
        for r in to_rows(after):
            print(f"    {r[0]}  {r[1]} [{r[2]}] by {r[3]}  {r[4]}")

    before_titles = {s["title"] for s, _, _ in before}
    after_titles = {s["title"] for s, _, _ in after}
    removed = before_titles - after_titles
    added = after_titles - before_titles
    print()
    if removed:
        print(f"  Removed: {', '.join(sorted(removed))}")
        print(f"  Replaced with: {', '.join(sorted(added))}")
    print()

    print("=" * 70)
    print("  All sections complete. Run `pytest tests/ -v` for full test suite.")
    print("=" * 70)


if __name__ == "__main__":
    main()
