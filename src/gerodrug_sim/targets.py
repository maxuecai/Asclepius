"""Target prediction and structure-driven Asclepius scoring."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable, Mapping

from gerodrug_sim.molecule import MoleculeProperties, analyze_smiles, molecular_fingerprint, tanimoto


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class AgingTarget:
    target_id: str
    target_name: str
    pathway: str
    hallmark_id: str
    hallmark_name: str
    evidence_level: str
    pdb_ids: tuple[str, ...]
    relevance: float
    notes: str = ""


@dataclass(frozen=True)
class KnownLigand:
    ligand_id: str
    name: str
    smiles: str
    target_id: str
    activity_type: str
    activity_value: str
    evidence: str = ""


@dataclass(frozen=True)
class TargetPrediction:
    target_id: str
    target_name: str
    hallmark_name: str
    pathway: str
    probability: float
    best_ligand: str
    similarity: float
    evidence_level: str
    pdb_ids: tuple[str, ...]
    target_relevance: float
    notes: str


def load_aging_targets(path: str | Path = ROOT / "data" / "aging_targets.csv") -> list[AgingTarget]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [
        AgingTarget(
            target_id=row["target_id"].strip(),
            target_name=row["target_name"].strip(),
            pathway=row["pathway"].strip(),
            hallmark_id=row["hallmark_id"].strip(),
            hallmark_name=row["hallmark_name"].strip(),
            evidence_level=row["evidence_level"].strip(),
            pdb_ids=tuple(part.strip() for part in row.get("pdb_ids", "").split(";") if part.strip()),
            relevance=float(row["relevance"]),
            notes=row.get("notes", "").strip(),
        )
        for row in rows
    ]


def load_known_ligands(path: str | Path = ROOT / "data" / "known_ligands.csv") -> list[KnownLigand]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [
        KnownLigand(
            ligand_id=row["ligand_id"].strip(),
            name=row["name"].strip(),
            smiles=row["smiles"].strip(),
            target_id=row["target_id"].strip(),
            activity_type=row.get("activity_type", "").strip(),
            activity_value=row.get("activity_value", "").strip(),
            evidence=row.get("evidence", "").strip(),
        )
        for row in rows
    ]


def predict_targets(
    smiles: str,
    targets: Iterable[AgingTarget] | None = None,
    ligands: Iterable[KnownLigand] | None = None,
    *,
    top_n: int = 8,
) -> list[TargetPrediction]:
    """Predict aging targets by ligand fingerprint similarity."""

    targets = list(targets or load_aging_targets())
    ligands = list(ligands or load_known_ligands())
    target_index = {target.target_id: target for target in targets}
    query_fp = molecular_fingerprint(smiles)
    best: dict[str, tuple[float, KnownLigand]] = {}
    for ligand in ligands:
        if ligand.target_id not in target_index:
            continue
        similarity = tanimoto(query_fp, molecular_fingerprint(ligand.smiles))
        if ligand.target_id not in best or similarity > best[ligand.target_id][0]:
            best[ligand.target_id] = (similarity, ligand)

    predictions: list[TargetPrediction] = []
    for target_id, (similarity, ligand) in best.items():
        target = target_index[target_id]
        probability = _probability_from_similarity(similarity, target.relevance, target.evidence_level)
        predictions.append(
            TargetPrediction(
                target_id=target.target_id,
                target_name=target.target_name,
                hallmark_name=target.hallmark_name,
                pathway=target.pathway,
                probability=round(probability, 3),
                best_ligand=ligand.name,
                similarity=round(similarity, 3),
                evidence_level=target.evidence_level,
                pdb_ids=target.pdb_ids,
                target_relevance=round(target.relevance, 3),
                notes=target.notes,
            )
        )
    return sorted(predictions, key=lambda item: (-item.probability, item.target_id))[:top_n]


def asclepius_score(
    properties: MoleculeProperties,
    predictions: Iterable[TargetPrediction],
    docking_score_norm: float = 0.5,
) -> dict[str, float]:
    """Compute a structure-driven Asclepius score."""

    predictions = list(predictions)
    top_probabilities = [prediction.probability for prediction in predictions[:3]]
    target_relevance = max(top_probabilities, default=0.0)
    aging_pathway_coverage = min(1.0, len({prediction.hallmark_name for prediction in predictions if prediction.probability >= 0.25}) / 4)
    safety_margin = _clamp(properties.oral_likeness - 0.10 * len(properties.pains_alerts) - 0.06 * len(properties.brenk_alerts))
    novelty = _clamp(1.0 - mean([prediction.similarity for prediction in predictions[:3]]) if predictions else 0.5)
    synthesis_feasibility = properties.synthetic_accessibility
    clinical_repositioning_potential = max(top_probabilities, default=0.0) * properties.oral_likeness
    admet_score = properties.oral_likeness
    drug_likeness = properties.qed
    components = {
        "target_relevance": target_relevance,
        "docking_score_norm": docking_score_norm,
        "admet_score": admet_score,
        "drug_likeness": drug_likeness,
        "novelty": novelty,
        "aging_pathway_coverage": aging_pathway_coverage,
        "safety_margin": safety_margin,
        "synthesis_feasibility": synthesis_feasibility,
        "clinical_repositioning_potential": clinical_repositioning_potential,
    }
    weights = {
        "target_relevance": 0.20,
        "docking_score_norm": 0.15,
        "admet_score": 0.15,
        "drug_likeness": 0.12,
        "novelty": 0.10,
        "aging_pathway_coverage": 0.10,
        "safety_margin": 0.08,
        "synthesis_feasibility": 0.05,
        "clinical_repositioning_potential": 0.05,
    }
    total = sum(components[key] * weights[key] for key in weights)
    return {"total": round(total, 3), **{key: round(value, 3) for key, value in components.items()}}


def _probability_from_similarity(similarity: float, relevance: float, evidence_level: str) -> float:
    evidence_bonus = {"high": 0.12, "medium": 0.07, "low": 0.02}.get(evidence_level.lower(), 0.04)
    return _clamp(similarity * 0.72 + relevance * 0.20 + evidence_bonus)


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))
