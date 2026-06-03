"""Docking orchestration with an executable fallback when Vina is unavailable."""

from __future__ import annotations

from dataclasses import dataclass
import shutil
from typing import Iterable

from gerodrug_sim.molecule import MoleculeProperties
from gerodrug_sim.targets import TargetPrediction


@dataclass(frozen=True)
class DockingResult:
    target_id: str
    target_name: str
    score_kcal_mol: float
    normalized_score: float
    backend: str
    notes: str


def run_docking_estimate(
    properties: MoleculeProperties,
    predictions: Iterable[TargetPrediction],
) -> list[DockingResult]:
    """Return docking-like scores; use Vina/smina metadata if installed, fallback otherwise."""

    backend = _detect_backend()
    results = []
    for prediction in list(predictions)[:5]:
        normalized = _clamp(
            0.28 * prediction.probability
            + 0.22 * properties.qed
            + 0.18 * properties.oral_likeness
            + 0.16 * properties.synthetic_accessibility
            + 0.16 * min(1.0, properties.molecular_weight / 500)
        )
        score = -4.0 - normalized * 6.5
        notes = "已检测到外部对接程序，可在后续版本接入受体 PDBQT 后运行真实 docking。" if backend != "heuristic" else "未检测到 Vina/smina，当前为结构性质 + 靶点概率的可解释估算。"
        results.append(
            DockingResult(
                target_id=prediction.target_id,
                target_name=prediction.target_name,
                score_kcal_mol=round(score, 2),
                normalized_score=round(normalized, 3),
                backend=backend,
                notes=notes,
            )
        )
    return sorted(results, key=lambda item: item.score_kcal_mol)


def _detect_backend() -> str:
    if shutil.which("vina"):
        return "vina-ready"
    if shutil.which("smina"):
        return "smina-ready"
    return "heuristic"


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))
