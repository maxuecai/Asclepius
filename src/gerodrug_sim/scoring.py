"""Deterministic candidate scoring for anti-aging drug R&D simulation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from gerodrug_sim.data import AgingHallmark, CandidateDrug


DEFAULT_COMPONENT_WEIGHTS = {
    "hallmark_target": 0.22,
    "expression_reversal": 0.18,
    "safety": 0.18,
    "translational_evidence": 0.16,
    "trial_feasibility": 0.10,
    "regulatory_readiness": 0.08,
    "biomarker_relevance": 0.08,
}


@dataclass(frozen=True)
class CandidateScore:
    """A ranked score with component-level traceability."""

    candidate_id: str
    name: str
    total_score: float
    components: dict[str, float]
    target_hallmarks: tuple[str, ...]
    evidence_sources: tuple[str, ...] = ()


def score_candidate(
    candidate: CandidateDrug,
    hallmarks: Mapping[str, AgingHallmark] | list[AgingHallmark],
    component_weights: Mapping[str, float] | None = None,
) -> CandidateScore:
    """Score a candidate using normalized weighted evidence components."""

    hallmark_index = _as_hallmark_index(hallmarks)
    weights = _validated_component_weights(component_weights or DEFAULT_COMPONENT_WEIGHTS)
    components = {
        "hallmark_target": hallmark_target_score(candidate, hallmark_index),
        "expression_reversal": candidate.expression_reversal,
        "safety": candidate.safety,
        "translational_evidence": candidate.translational_evidence,
        "trial_feasibility": candidate.trial_feasibility,
        "regulatory_readiness": candidate.regulatory_readiness,
        "biomarker_relevance": candidate.biomarker_relevance,
    }
    total = sum(components[name] * weights[name] for name in weights) / sum(weights.values())
    return CandidateScore(
        candidate_id=candidate.candidate_id,
        name=candidate.name,
        total_score=round(total, 6),
        components={name: round(value, 6) for name, value in components.items()},
        target_hallmarks=candidate.target_hallmarks,
        evidence_sources=candidate.evidence_sources,
    )


def rank_candidates(
    candidates: list[CandidateDrug],
    hallmarks: Mapping[str, AgingHallmark] | list[AgingHallmark],
    component_weights: Mapping[str, float] | None = None,
) -> list[CandidateScore]:
    """Return candidates sorted by descending total score, then stable ID."""

    scored = [
        score_candidate(candidate, hallmarks, component_weights=component_weights)
        for candidate in candidates
    ]
    return sorted(scored, key=lambda score: (-score.total_score, score.candidate_id))


def hallmark_target_score(
    candidate: CandidateDrug,
    hallmarks: Mapping[str, AgingHallmark] | list[AgingHallmark],
) -> float:
    """Compute coverage of weighted aging hallmarks for a candidate."""

    hallmark_index = _as_hallmark_index(hallmarks)
    total_weight = sum(hallmark.weight for hallmark in hallmark_index.values())
    if total_weight <= 0:
        raise ValueError("At least one hallmark must have positive total weight")

    missing = [hallmark_id for hallmark_id in candidate.target_hallmarks if hallmark_id not in hallmark_index]
    if missing:
        raise ValueError(
            f"Candidate {candidate.candidate_id!r} targets unknown hallmarks: {', '.join(missing)}"
        )

    targeted_weight = sum(hallmark_index[hallmark_id].weight for hallmark_id in set(candidate.target_hallmarks))
    return targeted_weight / total_weight


def _as_hallmark_index(
    hallmarks: Mapping[str, AgingHallmark] | list[AgingHallmark],
) -> Mapping[str, AgingHallmark]:
    if isinstance(hallmarks, Mapping):
        return hallmarks
    return {hallmark.hallmark_id: hallmark for hallmark in hallmarks}


def _validated_component_weights(weights: Mapping[str, float]) -> dict[str, float]:
    expected = set(DEFAULT_COMPONENT_WEIGHTS)
    actual = set(weights)
    if actual != expected:
        missing = expected - actual
        extra = actual - expected
        details = []
        if missing:
            details.append(f"missing: {', '.join(sorted(missing))}")
        if extra:
            details.append(f"extra: {', '.join(sorted(extra))}")
        raise ValueError(f"Component weights must match scoring components ({'; '.join(details)})")

    normalized = {name: float(value) for name, value in weights.items()}
    if any(value < 0.0 for value in normalized.values()):
        raise ValueError("Component weights must be non-negative")
    if sum(normalized.values()) <= 0.0:
        raise ValueError("At least one component weight must be positive")
    return normalized
