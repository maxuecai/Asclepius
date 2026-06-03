"""End-to-end molecular workflow for Asclepius."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from gerodrug_sim.admet import score_discovery_readiness, summarize_admet_risk
from gerodrug_sim.docking import run_docking_estimate
from gerodrug_sim.molecule import HAS_RDKIT, analyze_smiles, structure_svg
from gerodrug_sim.targets import asclepius_score, predict_targets


def analyze_molecule(smiles: str) -> dict[str, Any]:
    """Analyze a molecule from SMILES through target prediction and scoring."""

    properties = analyze_smiles(smiles)
    predictions = predict_targets(properties.smiles)
    docking_results = run_docking_estimate(properties, predictions)
    docking_norm = docking_results[0].normalized_score if docking_results else 0.5
    score = asclepius_score(properties, predictions, docking_score_norm=docking_norm)
    admet = summarize_admet_risk(properties)
    readiness = score_discovery_readiness(properties, predictions)
    return {
        "rdkit_available": HAS_RDKIT,
        "properties": asdict(properties),
        "predictions": [asdict(prediction) for prediction in predictions],
        "docking": [asdict(result) for result in docking_results],
        "admet": asdict(admet),
        "readiness": readiness,
        "score": score,
        "structure_svg": structure_svg(properties.smiles),
    }
