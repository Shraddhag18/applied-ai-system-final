"""
Agentic planning loop for the Music Recommender.

RecommendationAgent orchestrates a multi-step workflow:
  1. ANALYZE  — Parse profile, validate inputs
  2. RETRIEVE — Pull knowledge context (mood/genre similarity)
  3. SCORE    — Run enhanced scoring with retrieved knowledge
  4. CRITIQUE — Self-evaluate results (confidence, diversity, contradictions)
  5. REFINE   — If critique finds issues, adjust strategy and re-score
  6. EXPLAIN  — Generate final explanation with full reasoning chain

Every step is logged to AgentLog for full transparency.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from src.recommender import (
    load_songs, recommend_songs, apply_diversity_filter,
    score_song, SCORING_MODES, ScoringWeights,
)
from src.retrieval import KnowledgeBase, RetrievalContext
from src.guardrails import InputValidator, OutputGuardrail, ValidationResult
from src.confidence import ConfidenceScorer, ConfidenceResult
from src.bias_detector import BiasDetector


class PlanStep(Enum):
    ANALYZE = "analyze"
    RETRIEVE = "retrieve"
    SCORE = "score"
    CRITIQUE = "critique"
    REFINE = "refine"
    EXPLAIN = "explain"


@dataclass
class StepLog:
    """Record of one step in the agent's planning loop."""
    step: PlanStep
    input_summary: str
    output_summary: str
    decision: str = ""
    details: Dict = field(default_factory=dict)


@dataclass
class AgentLog:
    """Complete log of the agent's reasoning process."""
    profile_name: str
    steps: List[StepLog] = field(default_factory=list)
    final_mode: str = "balanced"
    refinement_applied: bool = False
    total_steps: int = 0

    def add(self, step: StepLog) -> None:
        self.steps.append(step)
        self.total_steps = len(self.steps)

    def summary(self) -> str:
        lines = [f"Agent Log for '{self.profile_name}' ({self.total_steps} steps):"]
        for i, s in enumerate(self.steps, 1):
            lines.append(f"  Step {i} [{s.step.value.upper()}]: {s.decision}")
        if self.refinement_applied:
            lines.append(f"  ** Refinement applied — switched to mode: {self.final_mode}")
        return "\n".join(lines)


@dataclass
class AgentResult:
    """Final output of the recommendation agent."""
    recommendations: List[Tuple]    # (song_dict, score, explanation)
    confidence: ConfidenceResult
    log: AgentLog
    warnings: List[str] = field(default_factory=list)


class RecommendationAgent:
    """
    Multi-step recommendation agent that plans, executes, critiques,
    and refines recommendations using knowledge retrieval and guardrails.
    """

    def __init__(self, songs: List[Dict], knowledge_base: KnowledgeBase):
        self.songs = songs
        self.kb = knowledge_base
        self.validator = InputValidator()
        self.guardrail = OutputGuardrail()
        self.confidence_scorer = ConfidenceScorer()
        self.bias_detector = BiasDetector()

    def run(self, profile_name: str, user_prefs: Dict, k: int = 5,
            mode: str = "balanced") -> AgentResult:
        """Execute the full agentic planning loop."""
        log = AgentLog(profile_name=profile_name)
        warnings: List[str] = []

        # ── Step 1: ANALYZE ─────────────────────────────────────────
        validation = self.validator.validate(user_prefs)
        analyze_decision = "Profile is valid" if validation.is_valid else "Profile has errors"
        if validation.warnings:
            analyze_decision += f" ({len(validation.warnings)} warnings)"
            warnings.extend(validation.warnings)

        log.add(StepLog(
            step=PlanStep.ANALYZE,
            input_summary=f"Profile: {profile_name}",
            output_summary=validation.summary(),
            decision=analyze_decision,
            details={"errors": validation.errors, "warnings": validation.warnings},
        ))

        if not validation.is_valid:
            return AgentResult(
                recommendations=[], warnings=validation.errors,
                confidence=ConfidenceResult(0, "LOW", {}, validation.errors, []),
                log=log,
            )

        # ── Step 2: RETRIEVE ────────────────────────────────────────
        context = self.kb.retrieve_context(user_prefs)
        retrieve_decision = "Knowledge context loaded"
        if context.warnings:
            retrieve_decision += f" with {len(context.warnings)} warnings"
            warnings.extend(context.warnings)

        log.add(StepLog(
            step=PlanStep.RETRIEVE,
            input_summary=f"genre={user_prefs.get('favorite_genre')}, mood={user_prefs.get('favorite_mood')}",
            output_summary=f"Mood context: {'yes' if context.has_mood else 'no'}, Genre context: {'yes' if context.has_genre else 'no'}",
            decision=retrieve_decision,
            details={"warnings": context.warnings},
        ))

        # ── Step 3: SCORE ───────────────────────────────────────────
        results = recommend_songs(user_prefs, self.songs, k=k, mode=mode)

        log.add(StepLog(
            step=PlanStep.SCORE,
            input_summary=f"mode={mode}, k={k}",
            output_summary=f"{len(results)} results, top score={results[0][1]:.2f}" if results else "0 results",
            decision=f"Scored {len(self.songs)} songs using '{mode}' mode",
        ))

        # ── Step 4: CRITIQUE ────────────────────────────────────────
        genre_ctx = context.genre_context if context.has_genre else None
        conf = self.confidence_scorer.score_confidence(
            results, user_prefs, self.songs, genre_ctx)

        catalog_genres = list({s.get("genre", "") for s in self.songs})
        quality = self.guardrail.check(
            results, max_possible_score=8.0,
            catalog_genres=catalog_genres,
            user_genre=user_prefs.get("favorite_genre", ""))

        critique_issues = conf.critique + quality.warnings
        critique_decision = f"Confidence={conf.level} ({conf.overall:.2f})"
        if not quality.passed:
            critique_decision += " — quality checks failed"

        log.add(StepLog(
            step=PlanStep.CRITIQUE,
            input_summary=f"{len(results)} results to evaluate",
            output_summary=f"Confidence: {conf.level}, Quality: {'PASS' if quality.passed else 'FAIL'}",
            decision=critique_decision,
            details={"confidence": conf.overall, "issues": critique_issues},
        ))

        # ── Step 5: REFINE (conditional) ────────────────────────────
        refined = False
        final_mode = mode

        if conf.level == "LOW" and mode == "balanced":
            # Try alternative modes to improve results
            best_mode = mode
            best_conf = conf.overall
            for alt_mode in ["mood_first", "energy_focused", "genre_first"]:
                alt_results = recommend_songs(user_prefs, self.songs, k=k, mode=alt_mode)
                alt_conf = self.confidence_scorer.score_confidence(
                    alt_results, user_prefs, self.songs, genre_ctx)
                if alt_conf.overall > best_conf:
                    best_conf = alt_conf.overall
                    best_mode = alt_mode
                    results = alt_results
                    conf = alt_conf
                    refined = True

            if refined:
                final_mode = best_mode
                log.add(StepLog(
                    step=PlanStep.REFINE,
                    input_summary=f"Low confidence ({conf.overall:.2f}) triggered refinement",
                    output_summary=f"Switched to '{best_mode}' mode (confidence: {best_conf:.2f})",
                    decision=f"Refined: {mode} -> {best_mode} (confidence {best_conf:.2f})",
                ))
            else:
                log.add(StepLog(
                    step=PlanStep.REFINE,
                    input_summary="Low confidence triggered refinement attempt",
                    output_summary="No better mode found — keeping original",
                    decision="No improvement found — kept balanced mode",
                ))
        else:
            log.add(StepLog(
                step=PlanStep.REFINE,
                input_summary=f"Confidence is {conf.level}",
                output_summary="No refinement needed",
                decision="Skipped — confidence is acceptable",
            ))

        log.final_mode = final_mode
        log.refinement_applied = refined

        # ── Step 6: EXPLAIN ─────────────────────────────────────────
        explain_parts = []
        if results:
            top_song, top_score, top_expl = results[0]
            explain_parts.append(f"Top pick: {top_song['title']} (score: {top_score:.2f})")
            explain_parts.append(f"Reasons: {top_expl}")
        explain_parts.append(f"Confidence: {conf.level} ({conf.overall:.2f})")
        if conf.critique:
            explain_parts.append(f"Notes: {'; '.join(conf.critique)}")

        log.add(StepLog(
            step=PlanStep.EXPLAIN,
            input_summary=f"{len(results)} final results",
            output_summary=explain_parts[0] if explain_parts else "No results",
            decision="Generated final explanation",
        ))

        return AgentResult(
            recommendations=results, confidence=conf,
            log=log, warnings=warnings,
        )
