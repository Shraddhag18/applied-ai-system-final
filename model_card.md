# Model Card: VibeFinder 1.0

---

## 1. Model Name

**VibeFinder 1.0** — a content-based music recommender simulation.

---

## 2. Goal / Task

VibeFinder tries to answer one question: *"Given what a listener says they want right now, which songs in the catalog are the best match?"*

It does not predict what a user will like based on past behavior. Instead, it scores songs against four preferences the user states directly — preferred genre, preferred mood, target energy level, and whether they like acoustic music — and returns the five highest-scoring songs. The output is a ranked list with a plain-language explanation for each pick.

This is a simulation, not a production system. Its purpose is to make the inner logic of a recommendation algorithm fully visible, so the decision-making process can be inspected, questioned, and improved.

---

## 3. Data Used

| Property | Detail |
|---|---|
| File | `data/songs.csv` |
| Songs in catalog | 18 |
| Genres covered | pop, lofi, rock, ambient, synthwave, jazz, indie pop, r&b, hip-hop, country, classical, electronic, folk, metal, reggae |
| Moods covered | happy, chill, intense, relaxed, moody, focused, romantic, nostalgic, sad, energetic, melancholic, angry |
| Numerical features per song | energy (0–1), tempo\_bpm, valence (0–1), danceability (0–1), acousticness (0–1) |

**Limits and gaps:** The catalog is tiny and Western-focused. Many major global genres — K-pop, Afrobeats, Bollywood, Latin, cumbia — are completely absent. Several genres (rock, classical, jazz) have only one song each, so those users will always see the same #1 result. The data was hand-curated for label diversity, not to reflect real listening popularity or demographic range.

---

## 4. Algorithm Summary

Think of VibeFinder as a very methodical friend who scores every song on a checklist before handing you a ranked playlist.

For each song in the catalog, the system asks four questions and awards points based on the answers:

1. **Does the genre match what you asked for?** If yes: +2.0 points. If no: +0. This is the strongest signal because genre is the broadest predictor of whether two songs belong together.

2. **Does the mood match?** If yes: +1.5 points. If no: +0. Mood is second most important, but it is categorical — "chill" and "relaxed" score the same as "chill" and "angry." There is no in-between.

3. **How close is the song's energy to your target?** A song at exactly your target energy gets +1.5 points. A song at the opposite extreme gets close to +0. Every song gets some points here — it rewards proximity, not just matching.

4. **Do you like acoustic music, and is this song acoustic?** If you said yes and the song scores above 0.6 on acousticness: +1.0 bonus point.

The maximum total score is **6.0 points**. After scoring all 18 songs, they are sorted from highest to lowest score, and the top 5 are shown with an explanation of which signals contributed.

**Why sorted() instead of sort():** The system uses Python's `sorted()` function, which returns a new sorted list without modifying the original. This means the same catalog can be scored for multiple user profiles in one run without reloading the CSV file.

---

## 5. Observed Behavior and Biases

### What works well

- **Profiles with matching catalog coverage** get excellent results. The Chill Lofi Student's top pick, Midnight Coding, scored 5.97/6.00 — all four signals fired simultaneously. The results feel right.
- **Distinct profiles produce distinct lists.** A lofi/chill user and a rock/intense user get completely different top fives from the same 18-song catalog. The scoring logic successfully differentiates listener types.
- **Every recommendation is explainable.** Each result shows exactly which signals contributed and how many points each added. There are no black-box decisions.

### Where it struggles — identified biases

**1. Genre lock-in creates filter bubbles.**
Genre carries +2.0 points — the highest weight — so any song in the user's preferred genre automatically outscores most songs that aren't. A lofi user's top three results are always the three lofi songs in the catalog, even if a folk or jazz track might be a better energy fit. In a real product, this pattern would keep users stuck in a narrow listening bubble and suppress discovery.

**2. Mood matching has no nuance.**
The system treats all non-matching moods as equally wrong. "Chill" and "relaxed" are neighbors in human experience, but they score 0 points apart — the same as "chill" and "angry." A jazz/relaxed user gets zero partial credit for a lofi/chill song. Users whose preferred mood has few catalog representatives are penalized harshly.

**3. Contradictory profiles are not detected.**
When genre + mood + acoustic (up to 4.5 points) overwhelm a large energy mismatch, the system makes counterintuitive recommendations. In testing, a user who asked for high energy (0.90) and classical music received Quiet Hours — a near-silent track with energy 0.22 — as the #1 result (4.98/6.00). The system has no mechanism to detect when a user's stated preferences conflict with each other.

**4. Missing genres fail silently.**
A user whose favorite genre is not in the catalog (tested with k-pop) can never score above ~3.0/6.00. The system returns five songs based on mood and energy alone, but it never tells the user that their genre is absent. The degraded results look the same as confident results.

**5. The acoustic signal is one-directional.**
Users who love acoustic sounds get a +1.0 bonus, but users who strongly dislike acoustic sounds receive no penalty on acoustic songs. An electronic-only listener will still see acoustic tracks appear if those songs match genre, mood, or energy well.

---

## 6. Evaluation Process

Six user profiles were tested: three designed to match the catalog well and three designed as adversarial or edge cases.

| Profile | Top Result | Score | What it tests |
|---|---|---|---|
| High-Energy Pop Fan | Sunrise City | 4.96 / 6.00 | Standard — well-covered genre |
| Chill Lofi Student | Midnight Coding | 5.97 / 6.00 | Standard — all 4 signals fire |
| Deep Intense Rock | Storm Runner | 5.00 / 6.00 | Standard — only 1 rock song in catalog |
| Conflicted (classical + sad + high energy) | Quiet Hours (energy=0.22!) | 4.98 / 6.00 | Adversarial — contradictory preferences |
| Unknown Genre (k-pop) | Sunrise City | 2.97 / 6.00 | Adversarial — genre not in catalog |
| Jazz / Relaxed / Middle Energy | Coffee Shop Stories | 5.80 / 6.00 | Edge case — only 1 jazz/relaxed song |

**Profile comparisons:**

- *Lofi/chill vs. Rock/intense:* The top five lists share zero songs. This confirms the genre weight is doing its job as the strongest differentiator — these two users live in completely separate parts of the catalog.

- *High-Energy Pop vs. Unknown Genre (k-pop):* Both users want high-energy, happy music. The pop fan's best result is 4.96/6.00; the k-pop fan's best is 2.97/6.00. The 1.99-point gap is entirely explained by the missing genre bonus. Same musical taste, very different experience — because the catalog does not represent the k-pop user.

- *Conflicted vs. Deep Intense Rock:* The rock fan wanted high energy and got it (Storm Runner, energy=0.91). The conflicted user also wanted high energy but got a near-silent classical track (energy=0.22). The difference is that the rock catalog match is consistent with the energy target, while the classical match is not — and the system cannot tell these situations apart.

**Weight experiment:**
Halving the genre weight (+1.0) and doubling the energy multiplier (×2.0, max 3.0) for the High-Energy Pop Fan shifted the #2 and #3 results: Rooftop Lights moved up (its energy 0.76 is closer to the 0.85 target than Gym Hero's 0.93) and Gym Hero dropped (it is tagged "intense" not "happy," so the missed mood signal cost more when energy dominated). The experiment confirmed that the current genre weight acts as a strong ranking anchor, and that weakening it produces more energy-sensitive, genre-agnostic results.

---

## 7. Intended Use and Non-Intended Use

### Intended use
- Classroom exploration and learning about how content-based recommendation algorithms work
- Demonstrating how weighted scoring, data representation, and catalog size affect outputs
- Practicing algorithmic thinking by tracing exactly why each result was ranked where it was

### Not intended for
- Real users making actual music listening decisions — the catalog is too small and too curated
- Any context where fairness across diverse listener backgrounds matters — global genres, languages, and cultural contexts are absent
- Inferring user preferences from behavior — the system requires users to state their preferences explicitly and has no memory or learning capability
- Production deployment — there is no error handling for malformed CSV data, no input validation, and no scalability for large catalogs

---

## 8. Ideas for Improvement

**Soft mood similarity.** Replace exact categorical mood matching with a similarity table where related moods ("chill" / "relaxed", "intense" / "angry") give partial credit. This would make the system more forgiving for users whose preferred mood has few catalog representatives.

**Catalog coverage signal.** When a user's preferred genre appears in fewer than three songs, print a notice: "Only 1 match found for genre=rock — showing best alternatives below." This is honest and helps users understand why their results look thin.

**Two-directional acoustic preference.** Add `dislikes_acoustic` as a penalty signal so users who want electronic-only music can push acoustic songs down the ranking, not just pull acoustic songs up.

**Tempo matching.** `tempo_bpm` is already in the CSV but is not used in scoring. Adding a target BPM preference (e.g., 80–100 BPM for studying, 130–150 for working out) would make the system meaningfully better for activity-based listening.

**Diversity enforcement.** After scoring, if the top five results are all the same genre, replace the lowest-scoring same-genre song with the top-scoring song from a different genre. This breaks the filter bubble slightly without requiring a full algorithm redesign.

---

## 9. Personal Reflection

**What was my biggest learning moment?**

The Conflicted profile test. I built the scoring formula fully expecting that a large energy mismatch would make a song uncompetitive. Instead, Quiet Hours — a near-silent classical piece with energy 0.22 — won the top spot for a user who asked for energy 0.90, scoring 4.98/6.00. The math was correct: genre match (+2.0) + mood match (+1.5) + acoustic bonus (+1.0) = 4.5 points before energy was even calculated. That moment showed me that every weight in a scoring formula is a design decision with real consequences, and that "the formula is working as intended" does not mean "the formula is doing what a real user would want."

**How did using AI tools help, and when did I need to double-check them?**

AI tools helped accelerate the research and structure phases significantly. I used them to quickly understand the difference between collaborative and content-based filtering, to generate the Mermaid.js flowchart syntax, and to brainstorm adversarial test profiles I might not have thought of on my own (like the contradictory energy + genre profile). However, I had to double-check any suggestion that involved the scoring math. Early on, an AI-suggested scoring function used `max(0, score)` clamps that would have silently hidden negative scores rather than letting me see them — that kind of silent fix is exactly the type of bug that causes real AI systems to behave unexpectedly. I also had to verify that `sorted()` (non-mutating) was the right choice over `list.sort()` for my use case, because the AI initially suggested `.sort()`, which would have modified the original catalog list and broken multi-profile runs.

**What surprised me about how simple algorithms can still "feel" like recommendations?**

The explanations made the difference. When the system says "#1 Midnight Coding — genre match: lofi (+2.0), mood match: chill (+1.5), energy proximity: 0.42 vs target 0.40 (+1.47), acoustic match (+1.0)," it feels credible and sensible — not because the algorithm is sophisticated, but because the reasoning is visible and aligns with how a person would justify the same pick. I think a big part of why recommendation systems "feel smart" in real products is not the algorithm itself but the framing around it. Hiding the weights and showing only the result makes even a simple formula seem mysterious and intelligent.

**What would I try next?**

I would add a second scoring pass that enforces diversity. After the initial ranking, if songs 1–3 are all the same genre, the system would insert the highest-scoring song from a different genre at position 3, pushing the duplicate down. This single change would break the filter bubble at minimal cost to relevance — and would make the system feel much more like a real music discovery tool rather than a catalog filter. I would also want to test what happens when the catalog grows to 200+ songs: at that scale, genre lock-in becomes less visible because there are many songs to choose from within each genre, and the energy and mood signals become the real differentiators.
