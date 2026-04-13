# Model Card: Music Recommender Simulation

## 1. Model Name

**VibeFinder 1.0**

---

## 2. Intended Use

VibeFinder 1.0 suggests up to five songs from a small 18-song catalog based on a listener's stated genre preference, mood preference, energy target, and acoustic taste. It is built for classroom exploration — to make the inner workings of a recommendation algorithm visible and inspectable — not for real production use. The system assumes the user can describe their preferences explicitly (e.g., "I want lofi, chill, low energy"). It makes no attempt to learn preferences over time or infer them from listening history.

---

## 3. How the Model Works

Imagine you tell a knowledgeable friend four things: your favorite genre, the mood you want right now, how energetic you want the music to feel (on a scale from 0 to 10), and whether you prefer acoustic or electronic sounds. That friend then goes through every song in a playlist one by one, awards points for how well each song matches your preferences, and hands you the five songs with the most points.

VibeFinder does exactly that. It awards up to 2.0 points for a genre match, 1.5 points if the mood matches, up to 1.5 points based on how close the song's energy level is to what you asked for (a song at exactly your target gets the full 1.5; a song at the opposite extreme gets close to 0), and 1.0 bonus point for acoustic songs if you said you like that sound. The maximum possible score is 6.0. Once every song has a score, they are sorted from highest to lowest and the top five are shown.

---

## 4. Data

The catalog contains **18 songs** stored in `data/songs.csv`. The original 10 songs cover pop, lofi, rock, ambient, synthwave, jazz, and indie pop. Eight additional songs were added to fill in missing genres: r&b, hip-hop, country, classical, electronic, folk, metal, and reggae. Moods represented include happy, chill, intense, relaxed, moody, focused, romantic, nostalgic, sad, energetic, melancholic, and angry.

The catalog is very small, Western-focused, and was hand-curated by the developer. Genres like Afrobeats, K-pop, Bollywood, and Latin are entirely absent. Because the dataset was assembled to cover diverse categorical labels (not to reflect real listening popularity), some genres have only one representative song. That means any user who prefers jazz, classical, or rock can only ever see one truly matching result — the rest of their top five will be based on mood or energy alone.

---

## 5. Strengths

- **Lofi / chill / acoustic users** receive excellent results. Midnight Coding scored 5.97/6.00 — all four signals fired — and the top two recommendations are clearly the right picks for that profile.
- **Rock / intense users** also get a clean result: Storm Runner scores a perfect 5.00 with an exact genre, mood, and energy match.
- **Explainability**: Every recommendation comes with a plain-language breakdown of exactly which signals contributed to its score. A user can look at any result and immediately understand why it was picked.
- **Profile contrast works**: Running the same catalog against a lofi profile versus a rock profile produces completely different top-five lists, which means the system successfully differentiates user types.

---

## 6. Limitations and Bias

**Genre lock-in creates filter bubbles.** Because genre is the highest-weighted signal (+2.0), any song that matches the user's genre automatically outscores nearly all songs that don't. A lofi user's top three results are always the three lofi songs in the catalog — they never escape their genre even if a folk or jazz song might be a better energy or mood match. In a real product this would leave users in a narrow listening bubble and reduce discovery.

**Categorical mood matching has no nuance.** The system treats "relaxed" and "chill" as completely different moods — the same distance apart as "relaxed" and "angry." A jazz/relaxed user gets zero credit for a lofi/chill song even though most people would experience those two vibes as close. This makes the system fragile for users whose preferred mood has few catalog representatives.

**Conflicting preferences expose a scoring gap.** When a user requests high energy (0.90) but their preferred genre and mood only appear in low-energy songs (like classical/sad), the system still recommends those low-energy songs because the genre and mood bonus (3.5 points) overwhelms the energy penalty. Quiet Hours scored 4.98/6.00 for a user targeting 0.90 energy, even though the song's energy is 0.22. The system has no way to flag when a user's profile is internally contradictory.

**Users whose genre is not in the catalog get mediocre results.** A k-pop user's best possible score is 2.97/6.00 — mood and energy only — because there are no k-pop songs to award the genre bonus. The system still returns five songs but never signals to the user that nothing in the catalog is a good match.

**The acoustic bonus is one-directional.** Users who prefer acoustic get a +1.0 bonus, but users who strongly dislike acoustic sounds get no penalty. An electronic-only listener will still see acoustic songs appear in their results if those songs match genre, mood, or energy well.

---

## 7. Evaluation

Six user profiles were tested, including three standard profiles and three adversarial / edge-case profiles:

| Profile | Top Result | Score | Observation |
|---|---|---|---|
| High-Energy Pop Fan | Sunrise City | 4.96 / 6.00 | Intuitive — genre + mood + close energy all fire |
| Chill Lofi Student | Midnight Coding | 5.97 / 6.00 | Near-perfect; all 4 signals fire |
| Deep Intense Rock | Storm Runner | 5.00 / 6.00 | Perfect genre + mood + exact energy match |
| Conflicted (high energy + sad classical + acoustic) | Quiet Hours | 4.98 / 6.00 | **Surprising** — song energy=0.22 beats all high-energy songs |
| Unknown Genre (k-pop) | Sunrise City | 2.97 / 6.00 | System degrades gracefully but max score is less than half |
| Perfectly Middle (jazz / relaxed / 0.5 energy) | Coffee Shop Stories | 5.80 / 6.00 | Works well; only one jazz/relaxed song in catalog |

**Most surprising result:** The Conflicted profile revealed that the sum of genre match (+2.0), mood match (+1.5), and acoustic bonus (+1.0) is 4.5 points — enough to outscore any song that only matches energy well. Quiet Hours won with 0.22 energy when the user asked for 0.90. The scoring formula cannot detect internal contradictions in a user profile.

**Weight experiment — doubling energy, halving genre:**
With genre reduced to +1.0 and energy raised to ×2.0 (max 3.0), the ranking for the High-Energy Pop Fan changed: Gym Hero dropped from #2 to #3 because it is tagged "intense" not "happy," and Rooftop Lights rose to #2 because its energy (0.76) is closer to the target than Gym Hero's (0.93). This shows the current genre weight acts as a strong tie-breaker; weakening it shifts the system toward pure energy matching and makes results more sensitive to the numerical target.

---

## 8. Future Work

- **Soft mood similarity**: Replace exact mood matching with a similarity lookup (e.g., "chill" and "relaxed" score 0.7 rather than 0.0). This would reduce the fragility for under-represented moods.
- **Catalog coverage signal**: When a user's genre has fewer than three songs in the catalog, surface a message like "Limited matches for this genre — showing best alternatives." This is honest and useful.
- **Negative preferences**: Let users specify what they want to avoid (e.g., `dislikes_acoustic=True` as a penalty) to make preferences two-directional.
- **Tempo matching**: Add `target_tempo_bpm` as a scored feature, since BPM is already in the data and is a strong predictor of whether a song "feels right" for a workout vs. studying.
- **Diversity enforcement**: After scoring, if the top 5 are all the same genre, swap in the top-scoring song from each other genre to add variety.

---

## 9. Personal Reflection

Building this made me realize how much work a seemingly simple recommendation — "here are five songs you might like" — is actually doing underneath. Every weight in the scoring formula is a design decision with real consequences: choosing genre as the strongest signal means the system will always prioritize staying in one genre over finding songs with the right energy or mood, which is sometimes the wrong call.

The Conflicted profile result was the most eye-opening moment. I assumed the energy check would catch obviously bad recommendations, but the math showed that two categorical matches easily overwhelm a large numerical gap. Real platforms like Spotify have to handle this same problem at enormous scale, which is why they use machine learning models that can learn from user behavior rather than fixed weights set by a developer.

The exercise also showed me that a recommendation system is only as good as its catalog. When k-pop was not in the dataset, the system could not help that user — no matter how clever the scoring logic. The data is the foundation.
