"""Deterministic aging digital twin and virtual trial simulation utilities."""

from __future__ import annotations

from dataclasses import dataclass, replace
import random
from statistics import mean
from typing import Callable, Iterable


@dataclass(frozen=True)
class ParticipantState:
    """A compact aging digital twin state for one simulated participant."""

    participant_id: str
    chronological_age: float
    aging_rate: float
    frailty_index: float
    inflammation: float
    mitochondrial_function: float
    biological_age_delta: float = 0.0


@dataclass(frozen=True)
class ArmResult:
    """Participant-level outcomes and aggregate metrics for a trial arm."""

    name: str
    baseline: tuple[ParticipantState, ...]
    final: tuple[ParticipantState, ...]
    metrics: dict[str, float]


@dataclass(frozen=True)
class VirtualTrialResult:
    """Placebo and treated arm outputs plus treatment contrasts."""

    placebo: ArmResult
    treated: ArmResult
    contrasts: dict[str, float]


def create_cohort(size: int, *, seed: int | None = None) -> tuple[ParticipantState, ...]:
    """Create a deterministic cohort of heterogeneous aging digital twins."""

    if size < 0:
        raise ValueError("size must be non-negative")

    rng = random.Random(seed)
    cohort: list[ParticipantState] = []
    for index in range(size):
        chronological_age = rng.uniform(55.0, 85.0)
        inflammation = _clamp(rng.gauss(0.48, 0.12))
        mitochondrial_function = _clamp(rng.gauss(0.62, 0.14))
        frailty_index = _clamp(
            0.08
            + (chronological_age - 55.0) * 0.012
            + inflammation * 0.22
            - mitochondrial_function * 0.12
            + rng.gauss(0.0, 0.04)
        )
        aging_rate = _clamp(
            0.85
            + inflammation * 0.35
            - mitochondrial_function * 0.22
            + frailty_index * 0.25
            + rng.gauss(0.0, 0.05),
            0.5,
            1.8,
        )
        biological_age_delta = (
            inflammation * 3.0
            + frailty_index * 4.5
            - mitochondrial_function * 2.0
            + rng.gauss(0.0, 0.7)
        )
        cohort.append(
            ParticipantState(
                participant_id=f"P{index + 1:04d}",
                chronological_age=chronological_age,
                aging_rate=aging_rate,
                frailty_index=frailty_index,
                inflammation=inflammation,
                mitochondrial_function=mitochondrial_function,
                biological_age_delta=biological_age_delta,
            )
        )
    return tuple(cohort)


def simulate_aging(
    participant: ParticipantState,
    *,
    years: float,
    treatment_effect: float = 0.0,
    seed: int | None = None,
) -> ParticipantState:
    """Advance one digital twin by ``years`` under placebo or treatment.

    ``treatment_effect`` is a normalized intervention strength from 0.0 to 1.0.
    Values near 1.0 represent a stronger geroprotective effect.
    """

    if years < 0:
        raise ValueError("years must be non-negative")
    if not 0.0 <= treatment_effect <= 1.0:
        raise ValueError("treatment_effect must be between 0.0 and 1.0")

    rng = random.Random(seed)
    state = participant
    remaining = years
    while remaining > 0.0:
        step_years = min(0.25, remaining)
        state = _simulate_step(state, step_years, treatment_effect, rng)
        remaining -= step_years
    return state


def run_virtual_trial(
    *,
    cohort_size: int = 100,
    years: float = 2.0,
    treatment_effect: float = 0.35,
    seed: int | None = None,
    cohort: Iterable[ParticipantState] | None = None,
) -> VirtualTrialResult:
    """Run matched placebo and treated arms and return summary metrics."""

    if cohort_size < 0:
        raise ValueError("cohort_size must be non-negative")
    if years < 0:
        raise ValueError("years must be non-negative")
    if not 0.0 <= treatment_effect <= 1.0:
        raise ValueError("treatment_effect must be between 0.0 and 1.0")

    baseline = tuple(cohort) if cohort is not None else create_cohort(cohort_size, seed=seed)
    if cohort is not None and cohort_size != 100 and cohort_size != len(baseline):
        raise ValueError("cohort_size must match provided cohort length")

    placebo_rng = random.Random(_derive_seed(seed, "placebo"))
    treated_rng = random.Random(_derive_seed(seed, "treated"))

    placebo_final = tuple(
        simulate_aging(
            participant,
            years=years,
            treatment_effect=0.0,
            seed=placebo_rng.randrange(2**32),
        )
        for participant in baseline
    )
    treated_final = tuple(
        simulate_aging(
            participant,
            years=years,
            treatment_effect=treatment_effect,
            seed=treated_rng.randrange(2**32),
        )
        for participant in baseline
    )

    placebo = ArmResult(
        name="placebo",
        baseline=baseline,
        final=placebo_final,
        metrics=summarize_arm(baseline, placebo_final),
    )
    treated = ArmResult(
        name="treated",
        baseline=baseline,
        final=treated_final,
        metrics=summarize_arm(baseline, treated_final),
    )
    return VirtualTrialResult(
        placebo=placebo,
        treated=treated,
        contrasts=_summarize_contrasts(placebo.metrics, treated.metrics),
    )


def summarize_arm(
    baseline: Iterable[ParticipantState],
    final: Iterable[ParticipantState],
) -> dict[str, float]:
    """Compute aggregate changes and endpoint metrics for one trial arm."""

    baseline_tuple = tuple(baseline)
    final_tuple = tuple(final)
    if len(baseline_tuple) != len(final_tuple):
        raise ValueError("baseline and final participant counts must match")
    if not baseline_tuple:
        return {
            "participants": 0.0,
            "mean_aging_rate_change": 0.0,
            "mean_frailty_index_change": 0.0,
            "mean_inflammation_change": 0.0,
            "mean_mitochondrial_function_change": 0.0,
            "mean_biological_age_delta_change": 0.0,
            "mean_final_biological_age_delta": 0.0,
            "responder_rate": 0.0,
        }

    return {
        "participants": float(len(baseline_tuple)),
        "mean_aging_rate_change": _mean_change(
            baseline_tuple, final_tuple, lambda state: state.aging_rate
        ),
        "mean_frailty_index_change": _mean_change(
            baseline_tuple, final_tuple, lambda state: state.frailty_index
        ),
        "mean_inflammation_change": _mean_change(
            baseline_tuple, final_tuple, lambda state: state.inflammation
        ),
        "mean_mitochondrial_function_change": _mean_change(
            baseline_tuple, final_tuple, lambda state: state.mitochondrial_function
        ),
        "mean_biological_age_delta_change": _mean_change(
            baseline_tuple, final_tuple, lambda state: state.biological_age_delta
        ),
        "mean_final_biological_age_delta": mean(
            state.biological_age_delta for state in final_tuple
        ),
        "responder_rate": mean(
            1.0
            if final_state.biological_age_delta <= baseline_state.biological_age_delta
            and final_state.frailty_index <= baseline_state.frailty_index
            else 0.0
            for baseline_state, final_state in zip(baseline_tuple, final_tuple)
        ),
    }


def _simulate_step(
    state: ParticipantState,
    years: float,
    treatment_effect: float,
    rng: random.Random,
) -> ParticipantState:
    inflammation_pressure = 0.035 + state.frailty_index * 0.02
    mitochondrial_decline = 0.025 + state.inflammation * 0.025
    frailty_pressure = 0.018 + state.inflammation * 0.03 - state.mitochondrial_function * 0.015

    inflammation = _clamp(
        state.inflammation
        + years * (inflammation_pressure - treatment_effect * 0.08)
        + rng.gauss(0.0, 0.008)
    )
    mitochondrial_function = _clamp(
        state.mitochondrial_function
        + years * (-mitochondrial_decline + treatment_effect * 0.07)
        + rng.gauss(0.0, 0.008)
    )
    frailty_index = _clamp(
        state.frailty_index
        + years * (frailty_pressure - treatment_effect * 0.035)
        + rng.gauss(0.0, 0.005)
    )
    aging_rate = _clamp(
        0.82
        + inflammation * 0.38
        - mitochondrial_function * 0.24
        + frailty_index * 0.28
        - treatment_effect * 0.12
        + rng.gauss(0.0, 0.015),
        0.45,
        1.9,
    )
    biological_age_delta = (
        state.biological_age_delta
        + years
        * (
            aging_rate
            - 1.0
            + inflammation * 0.22
            + frailty_index * 0.18
            - mitochondrial_function * 0.08
        )
        + rng.gauss(0.0, 0.03)
    )

    return replace(
        state,
        chronological_age=state.chronological_age + years,
        aging_rate=aging_rate,
        frailty_index=frailty_index,
        inflammation=inflammation,
        mitochondrial_function=mitochondrial_function,
        biological_age_delta=biological_age_delta,
    )


def _summarize_contrasts(
    placebo_metrics: dict[str, float],
    treated_metrics: dict[str, float],
) -> dict[str, float]:
    return {
        f"{metric}_difference": treated_metrics[metric] - placebo_metrics[metric]
        for metric in placebo_metrics
        if metric != "participants"
    }


def _mean_change(
    baseline: tuple[ParticipantState, ...],
    final: tuple[ParticipantState, ...],
    getter: Callable[[ParticipantState], float],
) -> float:
    return mean(getter(final_state) - getter(baseline_state) for baseline_state, final_state in zip(baseline, final))


def _derive_seed(seed: int | None, label: str) -> int | None:
    if seed is None:
        return None
    value = seed & 0xFFFFFFFF
    for character in label:
        value = (value * 1664525 + ord(character) + 1013904223) & 0xFFFFFFFF
    return value


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))
