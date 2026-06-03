"""Rule-based ADMET detail and portfolio sub-scores.

The project intentionally has no hard chemistry dependencies.  These helpers
therefore turn the existing :class:`MoleculeProperties` descriptors into
transparent, deterministic risk calls rather than opaque model predictions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from statistics import mean
from typing import Iterable

from gerodrug_sim.molecule import MoleculeProperties


CYP_ISOFORMS = ("1A2", "2C9", "2C19", "2D6", "3A4")

__all__ = [
    "ADMETRiskSummary",
    "CYP_ISOFORMS",
    "RiskCall",
    "admet_risk_summary",
    "discovery_readiness_subscores",
    "score_discovery_readiness",
    "summarize_admet_risk",
]


@dataclass(frozen=True)
class RiskCall:
    """One interpretable ADMET likelihood or risk call."""

    label: str
    level: str
    score: float
    rationale: tuple[str, ...]


@dataclass(frozen=True)
class ADMETRiskSummary:
    """Detailed ADMET summary derived from molecular descriptors."""

    gi_absorption: RiskCall
    pgp_substrate_likelihood: RiskCall
    cyp_isoform_risks: dict[str, RiskCall]
    dili_risk: RiskCall
    ames_risk: RiskCall
    mitochondrial_toxicity_risk: RiskCall
    uncertainty: RiskCall
    overall_safety_score: float


def summarize_admet_risk(properties: MoleculeProperties) -> ADMETRiskSummary:
    """Return a detailed, deterministic ADMET risk summary.

    Scores are normalized to 0..1.  For risk endpoints, higher means higher
    risk.  For GI absorption, higher means stronger absorption likelihood.
    """

    if not properties.valid:
        unknown = RiskCall("不可解析结构", "未知", 1.0, ("SMILES 解析失败，ADMET 只能标记为高不确定性。",))
        return ADMETRiskSummary(
            gi_absorption=unknown,
            pgp_substrate_likelihood=unknown,
            cyp_isoform_risks={isoform: unknown for isoform in CYP_ISOFORMS},
            dili_risk=unknown,
            ames_risk=unknown,
            mitochondrial_toxicity_risk=unknown,
            uncertainty=RiskCall("不确定性", "高", 1.0, ("无可用结构描述符。",)),
            overall_safety_score=0.0,
        )

    gi = _gi_absorption(properties)
    pgp = _pgp_substrate(properties)
    cyp = {isoform: _cyp_isoform_risk(properties, isoform) for isoform in CYP_ISOFORMS}
    dili = _dili_risk(properties)
    ames = _ames_risk(properties)
    mito = _mitochondrial_toxicity(properties)
    uncertainty = _uncertainty(properties)
    risk_values = [pgp.score, dili.score, ames.score, mito.score, *(call.score for call in cyp.values())]
    safety = _clamp(0.68 * (1.0 - mean(risk_values)) + 0.22 * gi.score + 0.10 * (1.0 - uncertainty.score))
    return ADMETRiskSummary(
        gi_absorption=gi,
        pgp_substrate_likelihood=pgp,
        cyp_isoform_risks=cyp,
        dili_risk=dili,
        ames_risk=ames,
        mitochondrial_toxicity_risk=mito,
        uncertainty=uncertainty,
        overall_safety_score=round(safety, 3),
    )


def admet_risk_summary(properties: MoleculeProperties) -> ADMETRiskSummary:
    """Backward-friendly alias for callers that prefer noun-style naming."""

    return summarize_admet_risk(properties)


def discovery_readiness_subscores(
    properties: MoleculeProperties,
    predictions: Iterable[object],
) -> dict[str, float]:
    """Map molecular properties and target predictions into four sub-scores.

    Returned keys are stable and additive: ``discovery``, ``safety``,
    ``translatability``, and ``evidence``.  Existing scoring APIs can consume
    these later without changing their current return shapes.
    """

    predictions = list(predictions)
    admet = summarize_admet_risk(properties)
    top_probability = max((_prediction_float(item, "probability") for item in predictions), default=0.0)
    top_relevance = max((_prediction_float(item, "target_relevance") for item in predictions), default=0.0)
    mean_similarity = mean([_prediction_float(item, "similarity") for item in predictions[:3]]) if predictions else 0.0
    coverage = len({_prediction_text(item, "hallmark_name") for item in predictions if _prediction_float(item, "probability") >= 0.25})
    evidence_quality = mean([_evidence_score(_prediction_text(item, "evidence_level")) for item in predictions[:5]]) if predictions else 0.0
    pdb_support = min(1.0, sum(1 for item in predictions[:5] if _prediction_tuple(item, "pdb_ids")) / 3)

    discovery = _clamp(
        0.36 * top_probability
        + 0.24 * properties.qed
        + 0.18 * properties.lead_likeness
        + 0.12 * min(1.0, coverage / 4)
        + 0.10 * (1.0 - mean_similarity)
    )
    safety = admet.overall_safety_score
    translatability = _clamp(
        0.28 * top_relevance
        + 0.22 * properties.oral_likeness
        + 0.18 * properties.synthetic_accessibility
        + 0.16 * admet.gi_absorption.score
        + 0.16 * (1.0 - admet.uncertainty.score)
    )
    evidence = _clamp(
        0.42 * evidence_quality
        + 0.24 * pdb_support
        + 0.20 * top_probability
        + 0.14 * min(1.0, coverage / 4)
    )
    return {
        "discovery": round(discovery, 3),
        "safety": round(safety, 3),
        "translatability": round(translatability, 3),
        "evidence": round(evidence, 3),
    }


def score_discovery_readiness(
    properties: MoleculeProperties,
    predictions: Iterable[object],
) -> dict[str, float]:
    """Alias with a verb-style name for scoring call sites."""

    return discovery_readiness_subscores(properties, predictions)


def _gi_absorption(properties: MoleculeProperties) -> RiskCall:
    score = properties.oral_likeness
    reasons = []
    if properties.molecular_weight > 500:
        score -= 0.18
        reasons.append("分子量超过 500 Da，口服吸收可能下降。")
    else:
        reasons.append("分子量处于常见口服药空间。")
    if properties.tpsa > 140:
        score -= 0.22
        reasons.append("TPSA 超过 140，肠道被动渗透不利。")
    elif properties.tpsa <= 120:
        score += 0.08
        reasons.append("TPSA 支持较好的肠道渗透。")
    if properties.hbd > 5 or properties.hba > 10:
        score -= 0.12
        reasons.append("氢键供受体数量偏高。")
    if properties.rotatable_bonds > 10:
        score -= 0.08
        reasons.append("可旋转键偏多，构象熵成本较高。")
    return RiskCall("GI absorption", _likelihood_level(score), round(_clamp(score), 3), tuple(reasons))


def _pgp_substrate(properties: MoleculeProperties) -> RiskCall:
    score = 0.18
    reasons = []
    if properties.molecular_weight >= 450:
        score += 0.18
        reasons.append("较高分子量增加 P-gp 外排底物可能性。")
    if properties.tpsa >= 90:
        score += 0.16
        reasons.append("TPSA 偏高常见于外排底物。")
    if properties.hba >= 7:
        score += 0.14
        reasons.append("氢键受体数量偏高。")
    if properties.rotatable_bonds >= 8:
        score += 0.12
        reasons.append("柔性偏高。")
    if properties.logp >= 3.5:
        score += 0.10
        reasons.append("脂溶性偏高。")
    if not reasons:
        reasons.append("尺寸、极性和柔性未显示明显 P-gp 底物特征。")
    return RiskCall("P-gp substrate likelihood", _risk_level(score), round(_clamp(score), 3), tuple(reasons))


def _cyp_isoform_risk(properties: MoleculeProperties, isoform: str) -> RiskCall:
    score = 0.12 + max(properties.logp - 2.5, 0.0) * 0.08 + properties.aromatic_rings * 0.05
    reasons = []
    if properties.logp > 3.0:
        reasons.append("LogP 偏高，提示 CYP 结合/抑制风险增加。")
    if properties.aromatic_rings >= 2:
        reasons.append("多芳香环结构增加 CYP 相互作用可能性。")
    if properties.molecular_weight > 450:
        score += 0.08
        reasons.append("分子量偏高。")
    if isoform == "1A2":
        score += 0.12 if properties.aromatic_rings >= 2 else 0.0
        reasons.append("1A2 对平面芳香结构更敏感。")
    elif isoform in {"2C9", "2C19"}:
        score += 0.10 if properties.logp >= 3.0 and properties.hba >= 3 else 0.0
        reasons.append(f"{isoform} 风险由脂溶性和氢键受体负担加权。")
    elif isoform == "2D6":
        score += 0.10 if properties.hba >= 4 and properties.logp >= 2.0 else 0.0
        reasons.append("2D6 风险由碱性/氢键受体代理特征估计。")
    elif isoform == "3A4":
        score += 0.14 if properties.molecular_weight >= 350 and properties.logp >= 3.0 else 0.0
        reasons.append("3A4 对较大且疏水的底物空间覆盖更广。")
    if properties.cyp_risk == "高":
        score += 0.12
        reasons.append("已有粗粒度 CYP 风险为高。")
    elif properties.cyp_risk == "中":
        score += 0.06
        reasons.append("已有粗粒度 CYP 风险为中。")
    return RiskCall(f"CYP{isoform}", _risk_level(score), round(_clamp(score), 3), tuple(reasons))


def _dili_risk(properties: MoleculeProperties) -> RiskCall:
    score = 0.14
    reasons = []
    if properties.hepatotoxicity_risk == "高":
        score += 0.34
        reasons.append("已有肝毒性规则为高风险。")
    elif properties.hepatotoxicity_risk == "中":
        score += 0.18
        reasons.append("已有肝毒性规则为中等风险。")
    if properties.logp > 3.5:
        score += 0.14
        reasons.append("高脂溶性与 DILI 风险负担相关。")
    if properties.molecular_weight > 450:
        score += 0.10
        reasons.append("较大分子增加代谢与胆汁排泄负担。")
    alert_count = len(properties.pains_alerts) + len(properties.brenk_alerts)
    if alert_count:
        score += min(0.24, alert_count * 0.10)
        reasons.append("结构警报增加反应性或非特异性安全风险。")
    if not reasons:
        reasons.append("未见明显 DILI 代理风险。")
    return RiskCall("DILI", _risk_level(score), round(_clamp(score), 3), tuple(reasons))


def _ames_risk(properties: MoleculeProperties) -> RiskCall:
    score = 0.10
    reasons = []
    alert_text = " ".join((*properties.pains_alerts, *properties.brenk_alerts))
    if "反应性" in alert_text or "非特异性" in alert_text:
        score += 0.28
        reasons.append("反应性/非特异性结构警报提示 Ames 风险。")
    if properties.aromatic_rings >= 3 and properties.hetero_atom_count >= 2:
        score += 0.16
        reasons.append("多芳香杂原子结构提高遗传毒性代理风险。")
    if properties.logp > 4.5:
        score += 0.08
        reasons.append("高脂溶性提高非特异性暴露风险。")
    if not reasons:
        reasons.append("未见强 Ames 结构警报代理信号。")
    return RiskCall("Ames mutagenicity", _risk_level(score), round(_clamp(score), 3), tuple(reasons))


def _mitochondrial_toxicity(properties: MoleculeProperties) -> RiskCall:
    score = 0.12
    reasons = []
    if properties.logp >= 4.0:
        score += 0.22
        reasons.append("高 LogP 可增加线粒体膜富集风险。")
    if properties.bbb_permeability == "可能较高":
        score += 0.08
        reasons.append("高膜通透性提示细胞器暴露可能增加。")
    if properties.molecular_weight >= 500:
        score += 0.10
        reasons.append("较大分子可能带来组织蓄积负担。")
    if properties.rotatable_bonds >= 10:
        score += 0.08
        reasons.append("高柔性提高非特异性结合代理风险。")
    if not reasons:
        reasons.append("未见明显线粒体毒性代理风险。")
    return RiskCall("Mitochondrial toxicity", _risk_level(score), round(_clamp(score), 3), tuple(reasons))


def _uncertainty(properties: MoleculeProperties) -> RiskCall:
    score = 0.18
    reasons = [f"描述符来源：{properties.engine}。"]
    if properties.engine != "RDKit":
        score += 0.28
        reasons.append("当前为轻量 SMILES 规则，结构描述符精度低于 RDKit。")
    if properties.heavy_atom_count < 6:
        score += 0.14
        reasons.append("结构过小，启发式适用性较弱。")
    if properties.pains_alerts or properties.brenk_alerts:
        score += 0.10
        reasons.append("存在结构警报，需要实验或外部模型复核。")
    if properties.lipinski_violations >= 2:
        score += 0.10
        reasons.append("Lipinski 违规较多，外推不确定性增加。")
    return RiskCall("Uncertainty", _risk_level(score), round(_clamp(score), 3), tuple(reasons))


def _prediction_float(prediction: object, key: str) -> float:
    value = _prediction_value(prediction, key, 0.0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _prediction_text(prediction: object, key: str) -> str:
    value = _prediction_value(prediction, key, "")
    return str(value or "")


def _prediction_tuple(prediction: object, key: str) -> tuple[object, ...]:
    value = _prediction_value(prediction, key, ())
    if value is None:
        return ()
    if isinstance(value, tuple):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(value)
    return (value,)


def _prediction_value(prediction: object, key: str, default: object) -> object:
    if isinstance(prediction, Mapping):
        return prediction.get(key, default)
    return getattr(prediction, key, default)


def _evidence_score(level: str) -> float:
    return {"high": 1.0, "medium": 0.68, "low": 0.38}.get(level.lower(), 0.5)


def _risk_level(score: float) -> str:
    score = _clamp(score)
    if score >= 0.66:
        return "高"
    if score >= 0.34:
        return "中"
    return "低"


def _likelihood_level(score: float) -> str:
    score = _clamp(score)
    if score >= 0.66:
        return "高"
    if score >= 0.34:
        return "中"
    return "低"


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))
