"""Command line workflow for the geroscience drug simulation prototype."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from gerodrug_sim.data import load_candidate_drugs, load_hallmarks
from gerodrug_sim.reporting import render_markdown_report
from gerodrug_sim.scoring import CandidateScore
from gerodrug_sim.scoring import rank_candidates
from gerodrug_sim.simulation import VirtualTrialResult, run_virtual_trial


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CANDIDATES = ROOT / "data" / "candidate_drugs.csv"
DEFAULT_HALLMARKS = ROOT / "data" / "aging_hallmarks.csv"
DEFAULT_OUTPUT = ROOT / "outputs" / "simulation_report.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rank geroscience drug candidates and simulate a small virtual trial."
    )
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--hallmarks", type=Path, default=DEFAULT_HALLMARKS)
    parser.add_argument("--condition", default="frailty prevention")
    parser.add_argument("--participants", type=int, default=240)
    parser.add_argument("--months", type=int, default=24)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def run_workflow(args: argparse.Namespace) -> Path:
    hallmarks = load_hallmarks(args.hallmarks)
    candidates = load_candidate_drugs(args.candidates)
    ranked = rank_candidates(candidates, hallmarks)[: args.top]

    trial_summaries = []
    for index, candidate in enumerate(ranked):
        trial_summaries.append(
            run_virtual_trial(
                cohort_size=args.participants,
                years=args.months / 12,
                treatment_effect=_score_to_treatment_effect(candidate.total_score),
                seed=args.seed + index,
            )
        )

    report = render_markdown_report(
        ranked_candidates=[
            _candidate_report_row(candidate, rank=index)
            for index, candidate in enumerate(ranked, start=1)
        ],
        trial_summaries=[
            _trial_report_row(args.condition, ranked[index].name, result, args.months)
            for index, result in enumerate(trial_summaries)
        ],
        title=f"Asclepius 模拟报告：{args.condition}",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    return args.output


def _score_to_treatment_effect(total_score: float) -> float:
    return max(0.05, min(0.75, total_score * 0.75))


def _candidate_report_row(candidate: CandidateScore, *, rank: int) -> dict[str, object]:
    safety = candidate.components.get("safety", 0.0)
    evidence = candidate.components.get("translational_evidence", 0.0)
    return {
        "id": candidate.candidate_id,
        "name": candidate.name,
        "mechanism": ", ".join(candidate.target_hallmarks),
        "score": candidate.total_score,
        "safety": safety,
        "evidence": f"translation {evidence:.2f}",
        "recommendation": _recommendation(rank, candidate.total_score, safety),
    }


def _trial_report_row(
    condition: str,
    candidate_name: str,
    result: VirtualTrialResult,
    months: int,
) -> dict[str, object]:
    responder_lift = result.contrasts["responder_rate_difference"]
    frailty_delta = result.contrasts["mean_frailty_index_change_difference"]
    bioage_delta = result.contrasts["mean_biological_age_delta_change_difference"]
    outcome = (
        f"responder lift {responder_lift:+.1%}; "
        f"frailty change {frailty_delta:+.3f}; "
        f"bio-age delta {bioage_delta:+.3f}"
    )
    return {
        "name": candidate_name,
        "phase": "virtual IIa",
        "population": condition,
        "duration": f"{months} months",
        "primary_endpoint": "frailty index + biological age delta",
        "outcome": outcome,
    }


def _recommendation(rank: int, score: float, safety: float) -> str:
    if rank == 1 and score >= 0.65 and safety >= 0.50:
        return "lead optimization"
    if score >= 0.55 and safety >= 0.45:
        return "validate in focused assays"
    return "hold for mechanism review"


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    output = run_workflow(args)
    print(f"Wrote report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
