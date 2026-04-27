# Reflection: VibeFinder 2.0 — Applied AI System

---

## What This Project Is

VibeFinder 2.0 extends my Module 3 Music Recommender Simulation into a full applied AI system. The original project (v1.0) was a content-based music recommender that scored songs against user preferences using a weighted formula. Version 2.0 adds RAG-style knowledge retrieval, an agentic planning loop, bias detection, guardrails, and reliability testing.

---

## v2.0 Profile Comparisons

### Chill Lofi Student — v1.0 vs v2.0

**v1.0:** Returns top 5 songs with scores and reasons. Confidence is unknown. No warnings.
**v2.0:** Returns top 5 songs + confidence=HIGH (0.86) + no warnings. The agent validates the profile, retrieves knowledge context (lofi genre info, chill mood neighbors), scores, and confirms high confidence. The system "knows it knows."

### Conflicted (Classical + Sad + High Energy) — v1.0 vs v2.0

**v1.0:** Silently recommends Quiet Hours (energy=0.22) to a user who asked for energy=0.90. Score: 4.98/6.00. No warning that the recommendation contradicts the user's energy preference.
**v2.0:** Still recommends Quiet Hours (scoring formula hasn't changed), but now flags it with confidence=MEDIUM (0.46) and explains why: "Energy 0.90 conflicts with 'classical' typical range [0.1–0.5]" and "Acoustic preference with high energy is unusual." The user now knows the system is unsure.

### Unknown Genre (K-pop) — v1.0 vs v2.0

**v1.0:** Returns 5 songs with low scores (max 2.97). No indication that k-pop is missing from the catalog. User has no way to know their genre isn't represented.
**v2.0:** Returns the same 5 songs but adds: "Genre 'k-pop' not in knowledge base — no songs in catalog will match by genre." Confidence drops to MEDIUM (0.50). The system is honest about its limitations.

---

## What I Learned About AI System Design

### 1. Confidence scoring is more valuable than better algorithms

The biggest improvement in v2.0 isn't a better scoring formula — it's knowing *when the formula is working well* and *when it isn't*. A system that returns a confident wrong answer is worse than one that returns the same wrong answer but says "I'm not sure about this." The confidence scorer's four factors (score quality, spread, genre coverage, profile coherence) together create a meaningful quality signal.

### 2. Guardrails operate at different levels

I initially thought "guardrails" meant input validation (checking types and ranges). But the rubric made me realize there are at least three levels:
- **Syntactic guardrails** (InputValidator): Is the energy value a number between 0 and 1?
- **Semantic guardrails** (Agent + ConfidenceScorer): Does high energy + classical music make sense together?
- **Systemic guardrails** (BiasDetector): Is the system fair across all user types?

Each level catches different problems. The syntactic validator alone only caught 40% of adversarial profiles. Adding the agent's confidence scoring raised the catch rate above 70%.

### 3. The knowledge base pattern is powerful but limited

RAG-style retrieval (mood taxonomy + genre guides) solved a real v1.0 problem: "chill" and "relaxed" were treated as completely different moods. The mood taxonomy gives them a similarity of 0.85. But the knowledge base is static — the similarity scores are hand-tuned, not learned from data. A real system would learn these relationships from user behavior.

### 4. Agentic loops need a clear stopping condition

The agent's 6-step loop (analyze → retrieve → score → critique → refine → explain) is effective, but the refine step needed careful design. Without a clear stopping condition, the agent could loop forever trying different modes. I solved this by only allowing one refinement attempt — if no alternative mode improves confidence, keep the original. This is a deliberate trade-off: simpler control flow at the cost of potentially missing a better mode combination.

---

## Fairness Analysis

The BiasDetector's fairness report across all 6 profiles revealed:

- **Fairness Score: 0.90/1.00** — good but not perfect
- **1 genre lockout** (K-pop fan gets zero genre matches)
- **0 dominant distributions** (no single song overwhelms every profile)
- **2 contradictory profiles** detected by the confidence scorer
- **2 low-diversity results** (lofi and rock profiles show genre lock-in)

The most impactful bias remains genre lock-in. The diversity filter helps (replacing Focus Flow with Coffee Shop Stories for the lofi student), but it's a band-aid. A real fix would require reducing genre weight or adding collaborative filtering.

---

## AI Collaboration

I used AI tools throughout the project:

**Helpful suggestions:**
- The agentic loop pattern with explicit critique and refine steps — this structure made the system much more transparent
- Designing the mood taxonomy with pairwise similarity scores — getting the relative distances right (chill/relaxed=0.85, chill/angry=0.0) was faster with AI assistance
- Suggesting adversarial test profiles I wouldn't have thought of (the contradictory energy + genre combination)

**Suggestions I had to verify or reject:**
- An early AI suggestion used `max(0, score)` clamps that would have hidden negative scores — I rejected this because silent error suppression makes systems harder to debug
- A suggestion to use cosine similarity for mood matching — this requires embedding vectors that don't exist in the system, so I used a lookup table instead
- An AI-suggested confidence formula that weighted all factors equally — I adjusted to give more weight to score quality and genre coverage because those are the factors users care most about

---

## What I Would Try Next

1. **Integrate soft matching into the main scoring formula** — The knowledge base already has mood/genre similarity scores ready to use. Replacing exact matching with soft matching in `score_song()` would be a single function change.
2. **Add a feedback loop** — Let users rate recommendations and adjust weights based on actual acceptance/rejection patterns.
3. **Expand the catalog** — At 200+ songs, genre lock-in becomes less visible because there are many songs within each genre. The energy and mood signals become the real differentiators at scale.
4. **Test with real users** — All current evaluation is algorithmic. Real users might value factors the confidence scorer doesn't measure.
