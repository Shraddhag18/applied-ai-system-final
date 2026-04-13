# Reflection: Profile Comparisons and Evaluation

---

## High-Energy Pop Fan vs. Chill Lofi Student

These two profiles produce completely different top-five lists with zero songs in common. The pop fan wants high-energy (0.85), happy music, while the lofi student wants low-energy (0.40), chill, acoustic music. Because genre is the strongest signal in the scoring formula, the pop fan's list is dominated by pop songs and the lofi student's list is dominated by lofi songs — even before mood or energy is considered. This makes sense: a lofi beat and a pop anthem rarely appeal to the same person at the same time, so a system that separates them is doing its job correctly.

---

## Chill Lofi Student vs. Deep Intense Rock

Both profiles got their #1 pick with high confidence — Midnight Coding scored 7.57 and Storm Runner scored 5.00 — but for different reasons. The lofi student benefited from advanced scoring bonuses (popularity match, decade match, mood tags) that pushed the score above the 6.0 base maximum. The rock fan got a near-perfect match on all four base signals (genre + mood + energy + acoustic), but their score was capped lower because the catalog only has one rock song. The interesting difference: the lofi student's list has variety at positions 4 and 5 (ambient, reggae), while the rock fan's list drops off sharply after #1 and fills with "intense mood but wrong genre" songs. This shows how catalog size shapes experience — the lofi student has three songs in their genre, the rock fan has one.

---

## High-Energy Pop Fan vs. Deep Intense Rock

Both users want high-energy music, but different flavors of it — happy pop vs. intense rock. Gym Hero (pop, intense, energy=0.93) appears at #2 for the pop fan even though its mood is "intense" not "happy." It earns that spot purely because it matches genre and has close energy. For the rock fan, Gym Hero also appears — at #2 — but this time for the opposite reason: it matches mood (intense) even though it is not rock. The same song surfaces for both users but for completely different signals. This is a good example of how the same catalog can serve different users reasonably well while still being a small dataset.

---

## Conflicted (High Energy + Sad + Acoustic + Classical) vs. High-Energy Pop Fan

This is the most revealing comparison. The conflicted user asked for high energy (0.90) but also preferred classical music, a sad mood, and acoustic sounds. The system gave them Quiet Hours — a near-silent classical track with energy 0.22 — as the #1 result. To a human listener, that recommendation makes no sense: the person said they wanted something energetic, and they got the opposite. But to the formula, it was correct: classical genre (+2.0) + sad mood (+1.5) + acoustic bonus (+1.0) = 4.5 points before energy was even counted, and a bad energy score could only subtract at most ~1.5 points from that total. The pop fan, by contrast, gets a recommendation (Sunrise City) that actually matches their energy target. The difference is that the pop catalog is consistent — pop songs tend to be high-energy — while the classical catalog is not. The system cannot detect when a user's preferences contradict each other internally.

---

## Unknown Genre (K-pop) vs. High-Energy Pop Fan

Both users want essentially the same kind of listening experience: happy, energetic, danceable music. The pop fan gets Sunrise City at 4.96/6.00. The k-pop fan's best result is Sunrise City at 2.97/6.00 — the exact same song, but scored almost 2 points lower. The 1.99-point gap comes entirely from the missing genre bonus (+2.0 for a genre match that never fires because k-pop is not in the catalog). In plain terms: the system silently gives k-pop users a worse experience than pop users, with no explanation. They see five songs, the songs are reasonable, but the scores are universally lower and the system never says "we don't have k-pop." This is a fairness problem — the quality of your recommendations depends on whether your culture or taste is represented in the dataset.

---

## Deep Intense Rock vs. Perfectly Middle (Jazz / Relaxed / 0.5 Energy)

Both users have only one song in their exact genre in the catalog (one rock song, one jazz/relaxed song), which means both profiles suffer from the same "genre lock-in" problem. Storm Runner and Coffee Shop Stories each win their respective #1 slots by wide margins. After #1, both lists fill with songs from other genres that match mood or energy instead. The rock fan's list skews high-energy (hip-hop, metal). The jazz fan's list skews low-energy and acoustic (reggae, folk). Even without genre match, the energy and acoustic signals are doing real work to differentiate the two users — showing that secondary signals matter once the primary signal (genre) runs out of candidates.

---

## Summary: What These Comparisons Show

The scoring formula works as intended — it reliably separates very different profiles and gives each user a distinct ranked list. The main failure modes are:

1. **When genre and other preferences conflict**, genre wins almost every time, even when the result feels wrong to a human (see: Conflicted profile).
2. **When a user's genre is absent or underrepresented**, the system degrades gracefully but silently — scores drop without explanation.
3. **Energy and mood are real secondary signals** — they do shape the bottom half of every list, and they become the primary differentiators once genre runs out of candidates.
