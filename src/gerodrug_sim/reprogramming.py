"""Scoring utilities for partial epigenetic reprogramming candidates."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FACTORS = ROOT / "data" / "reprogramming_factors.csv"


REPROGRAMMING_FACTOR_COLUMNS = (
    "factor_id",
    "name",
    "modality",
    "target_tissues",
    "rejuvenation_potential",
    "identity_preservation",
    "oncogenic_risk",
    "dedifferentiation_risk",
    "delivery_feasibility",
    "tissue_specificity",
    "evidence_strength",
    "druggability",
    "novelty_ip",
    "mechanism",
    "notes",
    "evidence_sources",
)


DEFAULT_REPROGRAMMING_WEIGHTS = {
    "rejuvenation_potential": 0.22,
    "identity_preservation": 0.16,
    "safety": 0.24,
    "delivery_feasibility": 0.10,
    "tissue_specificity": 0.08,
    "evidence_strength": 0.12,
    "druggability": 0.04,
    "novelty_ip": 0.04,
}


COMPONENT_LABELS = {
    "rejuvenation_potential": "年轻化潜力",
    "identity_preservation": "细胞身份保留",
    "safety": "安全性",
    "delivery_feasibility": "递送可行性",
    "tissue_specificity": "组织特异性",
    "evidence_strength": "证据强度",
    "druggability": "可药物化",
    "novelty_ip": "新颖性/IP空间",
}


@dataclass(frozen=True)
class ReprogrammingFactor:
    """A factor, cocktail, or modulation axis relevant to partial reprogramming."""

    factor_id: str
    name: str
    modality: str
    target_tissues: tuple[str, ...]
    rejuvenation_potential: float
    identity_preservation: float
    oncogenic_risk: float
    dedifferentiation_risk: float
    delivery_feasibility: float
    tissue_specificity: float
    evidence_strength: float
    druggability: float
    novelty_ip: float
    mechanism: str = ""
    notes: str = ""
    evidence_sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReprogrammingFactorScore:
    """A traceable ranking score for a reprogramming candidate."""

    factor_id: str
    name: str
    priority_score: float
    safety_score: float
    components: dict[str, float]
    target_tissues: tuple[str, ...]
    modality: str
    mechanism: str
    recommendation: str
    notes: str = ""
    evidence_sources: tuple[str, ...] = ()
    evidence_basis: str = "curated"
    literature_count: int = 0
    safety_warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReprogrammingCombination:
    """A conservative research design for combining reprogramming factors."""

    combination_id: str
    name: str
    factor_ids: tuple[str, ...]
    factor_names: tuple[str, ...]
    target_tissue: str
    risk_profile: str
    strategy: str
    priority_score: float
    safety_score: float
    rationale: tuple[str, ...]
    excluded_factors: tuple[str, ...]
    validation_plan: tuple[str, ...]


@dataclass(frozen=True)
class TissueReprogrammingPlan:
    """A tissue-first research route for partial reprogramming."""

    tissue: str
    label: str
    priority: float
    lead_factors: tuple[str, ...]
    lead_combination: str
    model_system: str
    delivery_focus: str
    primary_readouts: tuple[str, ...]
    safety_focus: tuple[str, ...]
    next_actions: tuple[str, ...]


def load_reprogramming_factors(path: str | Path = DEFAULT_FACTORS) -> list[ReprogrammingFactor]:
    """Load curated reprogramming candidates from CSV."""

    rows = _read_rows(path, REPROGRAMMING_FACTOR_COLUMNS)
    factors = [
        ReprogrammingFactor(
            factor_id=_required(row, "factor_id"),
            name=_required(row, "name"),
            modality=_required(row, "modality"),
            target_tissues=_split_ids(row.get("target_tissues", "")),
            rejuvenation_potential=_bounded_float(row, "rejuvenation_potential"),
            identity_preservation=_bounded_float(row, "identity_preservation"),
            oncogenic_risk=_bounded_float(row, "oncogenic_risk"),
            dedifferentiation_risk=_bounded_float(row, "dedifferentiation_risk"),
            delivery_feasibility=_bounded_float(row, "delivery_feasibility"),
            tissue_specificity=_bounded_float(row, "tissue_specificity"),
            evidence_strength=_bounded_float(row, "evidence_strength"),
            druggability=_bounded_float(row, "druggability"),
            novelty_ip=_bounded_float(row, "novelty_ip"),
            mechanism=row.get("mechanism", "").strip(),
            notes=row.get("notes", "").strip(),
            evidence_sources=_split_optional_ids(row.get("evidence_sources", "")),
        )
        for row in rows
    ]
    _ensure_unique("factor_id", [factor.factor_id for factor in factors])
    return factors


def score_reprogramming_factor(
    factor: ReprogrammingFactor,
    component_weights: Mapping[str, float] | None = None,
) -> ReprogrammingFactorScore:
    """Score a factor for safe, targeted partial reprogramming priority."""

    weights = _validated_weights(component_weights or DEFAULT_REPROGRAMMING_WEIGHTS)
    safety_score = reprogramming_safety_score(factor)
    components = {
        "rejuvenation_potential": factor.rejuvenation_potential,
        "identity_preservation": factor.identity_preservation,
        "safety": safety_score,
        "delivery_feasibility": factor.delivery_feasibility,
        "tissue_specificity": factor.tissue_specificity,
        "evidence_strength": factor.evidence_strength,
        "druggability": factor.druggability,
        "novelty_ip": factor.novelty_ip,
    }
    total = sum(components[name] * weights[name] for name in weights) / sum(weights.values())
    priority_score = round(total, 6)
    return ReprogrammingFactorScore(
        factor_id=factor.factor_id,
        name=factor.name,
        priority_score=priority_score,
        safety_score=round(safety_score, 6),
        components={name: round(value, 6) for name, value in components.items()},
        target_tissues=factor.target_tissues,
        modality=factor.modality,
        mechanism=factor.mechanism,
        recommendation=reprogramming_recommendation(priority_score, safety_score),
        notes=factor.notes,
        evidence_sources=factor.evidence_sources,
        evidence_basis="curated",
    )


def rank_reprogramming_factors(
    factors: Iterable[ReprogrammingFactor],
    component_weights: Mapping[str, float] | None = None,
) -> list[ReprogrammingFactorScore]:
    """Return factors sorted by safe-rejuvenation priority."""

    scored = [
        score_reprogramming_factor(factor, component_weights=component_weights)
        for factor in factors
    ]
    return sorted(scored, key=lambda score: (-score.priority_score, -score.safety_score, score.factor_id))


def score_reprogramming_factor_with_literature(
    factor: ReprogrammingFactor,
    papers: Iterable[object],
    component_weights: Mapping[str, float] | None = None,
) -> ReprogrammingFactorScore:
    """Score a factor after adjusting evidence and risk from local papers."""

    papers = list(papers)
    if not papers:
        return score_reprogramming_factor(factor, component_weights=component_weights)
    evidence_scores = [_signal_value(paper, "evidence_score") for paper in papers]
    average_evidence = sum(evidence_scores) / len(evidence_scores) if evidence_scores else factor.evidence_strength
    risk_terms = sorted(
        {
            risk
            for paper in papers
            for risk in _signal_tuple(paper, "safety_risks")
        }
    )
    tissue_terms = {
        tissue
        for paper in papers
        for tissue in _signal_tuple(paper, "tissues")
    }
    functional_readout_count = sum(
        1 for paper in papers if "function" in _signal_tuple(paper, "readouts")
    )
    evidence_strength = _clamp(factor.evidence_strength * 0.45 + average_evidence * 0.55 + min(0.08, 0.01 * len(papers)))
    oncogenic_risk = _clamp(factor.oncogenic_risk + 0.04 * len([risk for risk in risk_terms if risk == "oncogenic risk"]))
    dedifferentiation_risk = _clamp(
        factor.dedifferentiation_risk + 0.04 * len([risk for risk in risk_terms if risk == "dedifferentiation"])
    )
    tissue_specificity = _clamp(factor.tissue_specificity + min(0.08, 0.02 * len(tissue_terms)))
    rejuvenation_potential = _clamp(factor.rejuvenation_potential + min(0.06, 0.015 * functional_readout_count))
    adjusted = ReprogrammingFactor(
        factor_id=factor.factor_id,
        name=factor.name,
        modality=factor.modality,
        target_tissues=factor.target_tissues,
        rejuvenation_potential=rejuvenation_potential,
        identity_preservation=factor.identity_preservation,
        oncogenic_risk=oncogenic_risk,
        dedifferentiation_risk=dedifferentiation_risk,
        delivery_feasibility=factor.delivery_feasibility,
        tissue_specificity=tissue_specificity,
        evidence_strength=evidence_strength,
        druggability=factor.druggability,
        novelty_ip=factor.novelty_ip,
        mechanism=factor.mechanism,
        notes=factor.notes,
        evidence_sources=factor.evidence_sources,
    )
    score = score_reprogramming_factor(adjusted, component_weights=component_weights)
    return ReprogrammingFactorScore(
        factor_id=score.factor_id,
        name=score.name,
        priority_score=score.priority_score,
        safety_score=score.safety_score,
        components=score.components,
        target_tissues=score.target_tissues,
        modality=score.modality,
        mechanism=score.mechanism,
        recommendation=score.recommendation,
        notes=score.notes,
        evidence_sources=score.evidence_sources,
        evidence_basis="literature_adjusted",
        literature_count=len(papers),
        safety_warnings=tuple(risk_terms),
    )


def rank_reprogramming_factors_with_literature(
    factors: Iterable[ReprogrammingFactor],
    papers_by_factor: Mapping[str, Iterable[object]],
    component_weights: Mapping[str, float] | None = None,
) -> list[ReprogrammingFactorScore]:
    """Rank factors using local literature as an evidence/risk adjustment layer."""

    scored = [
        score_reprogramming_factor_with_literature(
            factor,
            papers_by_factor.get(factor.factor_id, ()),
            component_weights=component_weights,
        )
        for factor in factors
    ]
    return sorted(scored, key=lambda score: (-score.priority_score, -score.safety_score, score.factor_id))


def reprogramming_safety_score(factor: ReprogrammingFactor) -> float:
    """Convert tumor and identity-loss risks into a normalized safety score."""

    risk = factor.oncogenic_risk * 0.62 + factor.dedifferentiation_risk * 0.38
    return _clamp(1.0 - risk)


def reprogramming_recommendation(priority_score: float, safety_score: float) -> str:
    """Translate numeric scores into a conservative research action."""

    if priority_score >= 0.68 and safety_score >= 0.55:
        return "prioritize focused validation"
    if priority_score >= 0.58 and safety_score >= 0.45:
        return "watchlist with safety gates"
    if safety_score < 0.35:
        return "benchmark only; high-risk"
    return "hold for mechanism review"


def reprogramming_report_rows(scores: Iterable[ReprogrammingFactorScore]) -> list[dict[str, object]]:
    """Build JSON/Markdown-friendly rows for reports or GUI payloads."""

    rows = []
    for rank, score in enumerate(scores, start=1):
        rows.append(
            {
                "rank": rank,
                "id": score.factor_id,
                "name": score.name,
                "modality": score.modality,
                "tissues": "、".join(score.target_tissues),
                "score": score.priority_score,
                "safety": score.safety_score,
                "recommendation": _localized_recommendation(score.recommendation),
                "mechanism": score.mechanism,
                "notes": score.notes,
                "components": score.components,
                "evidence_sources": list(score.evidence_sources),
                "evidence_basis": score.evidence_basis,
                "literature_count": score.literature_count,
                "safety_warnings": list(score.safety_warnings),
                "process_notes": explain_reprogramming_score(score),
                "next_steps": suggest_reprogramming_next_steps(score),
            }
        )
    return rows


def design_reprogramming_combinations(
    scores: Iterable[ReprogrammingFactorScore],
    target_tissue: str = "fibroblast",
    risk_profile: str = "conservative",
) -> list[ReprogrammingCombination]:
    """Design traceable factor-combination strategies for early validation."""

    scored = list(scores)
    if not scored:
        return []
    by_id = {score.factor_id: score for score in scored}
    tissue = target_tissue.strip() or "fibroblast"
    profile = risk_profile.strip().lower() or "conservative"
    tissue_matched = [
        score
        for score in scored
        if tissue in score.target_tissues or "fibroblast" in score.target_tissues
    ]
    if not tissue_matched:
        tissue_matched = scored
    excluded = tuple(
        score.name
        for score in scored
        if score.safety_score < 0.35 or score.factor_id in {"myc", "oskm"}
    )
    support_pool = [
        score
        for score in tissue_matched
        if score.safety_score >= 0.55
        and score.components.get("identity_preservation", 0.0) >= 0.65
        and score.factor_id not in {"osk", "oskm", "myc"}
    ]
    support_pool = sorted(
        support_pool,
        key=lambda score: (-score.safety_score, -score.priority_score, score.factor_id),
    )
    combinations: list[ReprogrammingCombination] = []
    support = tuple(support_pool[:3])
    if support:
        combinations.append(
            _make_combination(
                combination_id="low_risk_support_axis",
                name="低风险染色质/稳态支持轴",
                factors=support,
                target_tissue=tissue,
                risk_profile=profile,
                strategy="先用安全性较高的染色质修复、应激稳态或表观调控轴建立低风险年轻化基线。",
                rationale=(
                    "优先选择身份保留和安全分较高的因子，避免直接推动多能性状态。",
                    "适合作为体外筛选的第一批组合，帮助校准年轻化 readout 与安全 readout。",
                    "若效果弱，可作为 OSK 短暂表达方案的安全辅助轴，而不是单独押注。",
                ),
                excluded_factors=excluded,
                validation_plan=_combination_validation_plan(support, tissue, "low_risk"),
            )
        )

    osk = by_id.get("osk")
    support_for_osk = tuple(
        score
        for score in support_pool
        if score.factor_id not in {"oct4", "sox2", "klf4"}
    )[:2]
    if osk and osk.safety_score >= 0.35:
        factors = (osk, *support_for_osk)
        combinations.append(
            _make_combination(
                combination_id="gated_osk_core",
                name="OSK 短暂表达 + 安全辅助轴",
                factors=factors,
                target_tissue=tissue,
                risk_profile=profile,
                strategy="把 OSK 作为年轻化核心信号，但只允许短时程、局部、可关闭表达，并配套低风险支持轴。",
                rationale=(
                    "OSK 的年轻化信号最强，但安全窗口窄，必须把表达时长和组织范围作为核心变量。",
                    "组合中不加入 MYC；支持轴用于提高身份稳定、DNA 修复或应激耐受。",
                    "适合做第二阶段验证：先证明撤除后年轻化 signature 能保留，且多能性/增殖标志不上升。",
                ),
                excluded_factors=excluded,
                validation_plan=_combination_validation_plan(factors, tissue, "gated_osk"),
            )
        )

    benchmark = tuple(score for score in (by_id.get("oskm") or by_id.get("myc"),) if score)
    if benchmark:
        combinations.append(
            _make_combination(
                combination_id="high_risk_benchmark",
                name="高风险重编程基准",
                factors=benchmark,
                target_tissue=tissue,
                risk_profile="benchmark_only",
                strategy="只作为风险上限和阳性基准，帮助模型识别去分化、异常增殖和癌变信号。",
                rationale=(
                    "OSKM/MYC 可以提供强重编程信号，但不应作为治疗候选直接推进。",
                    "这个组合的价值在于建立风险标签和模型边界，而不是追求产品化。",
                    "任何低风险方案都应在年轻化效果接近时显著低于该基准的风险 readout。",
                ),
                excluded_factors=(),
                validation_plan=_combination_validation_plan(benchmark, tissue, "benchmark"),
            )
        )

    return sorted(combinations, key=lambda combo: (-combo.priority_score, -combo.safety_score, combo.combination_id))


def combination_report_rows(combinations: Iterable[ReprogrammingCombination]) -> list[dict[str, object]]:
    """Build GUI/report rows for combination strategies."""

    rows = []
    for rank, combo in enumerate(combinations, start=1):
        rows.append(
            {
                "rank": rank,
                "id": combo.combination_id,
                "name": combo.name,
                "factors": " + ".join(combo.factor_names),
                "factor_ids": list(combo.factor_ids),
                "target_tissue": combo.target_tissue,
                "risk_profile": _localized_risk_profile(combo.risk_profile),
                "strategy": combo.strategy,
                "score": combo.priority_score,
                "safety": combo.safety_score,
                "rationale": list(combo.rationale),
                "excluded_factors": list(combo.excluded_factors),
                "validation_plan": list(combo.validation_plan),
            }
        )
    return rows


def design_tissue_reprogramming_plans(
    scores: Iterable[ReprogrammingFactorScore],
    combinations: Iterable[ReprogrammingCombination],
    focus_tissues: Iterable[str] = ("fibroblast", "retina", "muscle", "immune", "neuron"),
) -> list[TissueReprogrammingPlan]:
    """Create tissue-specific roadmaps from factor scores and combination designs."""

    scored = list(scores)
    combos = list(combinations)
    plans = []
    seen_tissues: set[str] = set()
    for tissue in focus_tissues:
        if tissue in seen_tissues:
            continue
        seen_tissues.add(tissue)
        matched = [
            score
            for score in scored
            if tissue in score.target_tissues or _tissue_family_match(tissue, score.target_tissues)
        ]
        if not matched:
            continue
        matched = sorted(matched, key=lambda score: (-score.priority_score, -score.safety_score, score.factor_id))
        safe_matched = [score for score in matched if score.safety_score >= 0.45]
        lead_scores = safe_matched[:3] or matched[:3]
        lead_combo = _best_combo_for_tissue(combos, tissue)
        profile = _tissue_profile(tissue)
        priority = _clamp(
            sum(score.priority_score for score in lead_scores) / len(lead_scores)
            + (0.05 if lead_combo and lead_combo.safety_score >= 0.55 else 0.0)
            - (0.05 if not safe_matched else 0.0)
        )
        plans.append(
            TissueReprogrammingPlan(
                tissue=tissue,
                label=profile["label"],
                priority=round(priority, 6),
                lead_factors=tuple(score.name for score in lead_scores),
                lead_combination=lead_combo.name if lead_combo else "暂无组合；先补因子证据",
                model_system=profile["model"],
                delivery_focus=profile["delivery"],
                primary_readouts=tuple(profile["readouts"]),
                safety_focus=tuple(profile["safety"]),
                next_actions=_tissue_next_actions(tissue, lead_scores, lead_combo),
            )
        )
    return sorted(plans, key=lambda plan: (-plan.priority, plan.tissue))


def tissue_plan_report_rows(plans: Iterable[TissueReprogrammingPlan]) -> list[dict[str, object]]:
    """Build GUI/report rows for tissue-first roadmaps."""

    rows = []
    for rank, plan in enumerate(plans, start=1):
        rows.append(
            {
                "rank": rank,
                "tissue": plan.tissue,
                "label": plan.label,
                "priority": plan.priority,
                "lead_factors": " + ".join(plan.lead_factors),
                "lead_combination": plan.lead_combination,
                "model_system": plan.model_system,
                "delivery_focus": plan.delivery_focus,
                "primary_readouts": list(plan.primary_readouts),
                "safety_focus": list(plan.safety_focus),
                "next_actions": list(plan.next_actions),
            }
        )
    return rows


def safety_gate_rows(items: Iterable[ReprogrammingFactorScore | ReprogrammingCombination]) -> list[dict[str, object]]:
    """Create a stop/go safety matrix for factors and combinations."""

    rows = []
    for item in items:
        name = getattr(item, "name")
        safety = float(getattr(item, "safety_score"))
        item_id = getattr(item, "factor_id", getattr(item, "combination_id", name))
        level = "red" if safety < 0.35 else "amber" if safety < 0.55 else "green"
        rows.append(
            {
                "id": item_id,
                "name": name,
                "gate": _localized_gate(level),
                "safety": round(safety, 6),
                "must_pass": list(_must_pass_readouts(level)),
                "stop_triggers": list(_stop_triggers(level)),
                "cadence": "每个表达窗口、撤除后稳定窗口、长期观察窗口都要复核",
            }
        )
    return sorted(rows, key=lambda row: (row["gate"] != "红灯", row["gate"] != "黄灯", str(row["name"])))


def evidence_gap_rows(scores: Iterable[ReprogrammingFactorScore]) -> list[dict[str, object]]:
    """Rank missing evidence tasks for the local AI literature workflow."""

    rows = []
    for score in scores:
        gaps = []
        if score.literature_count < 3:
            gaps.append("本地文献不足")
        if score.components.get("evidence_strength", 0.0) < 0.6:
            gaps.append("证据强度不足")
        if score.components.get("delivery_feasibility", 0.0) < 0.55:
            gaps.append("递送可控性不足")
        if score.safety_score < 0.55:
            gaps.append("安全窗口不足")
        if score.components.get("identity_preservation", 0.0) < 0.6:
            gaps.append("身份保留不足")
        if not gaps:
            gaps.append("证据相对完整；进入交叉验证")
        urgency = _gap_urgency(score, gaps)
        rows.append(
            {
                "id": score.factor_id,
                "name": score.name,
                "urgency": urgency,
                "gaps": gaps,
                "query": _gap_query(score),
                "ai_task": _gap_ai_task(score, gaps),
            }
        )
    return sorted(rows, key=lambda row: (-float(row["urgency"]), str(row["name"])))


def evidence_attribution_rows(papers: Iterable[object]) -> list[dict[str, object]]:
    """Explain how each paper contributes to a factor-level judgment."""

    rows = []
    for paper in papers:
        signals = getattr(paper, "signals", None)
        evidence_score = float(getattr(signals, "evidence_score", 0.0) or 0.0)
        models = _as_tuple(getattr(signals, "models", ()))
        readouts = _as_tuple(getattr(signals, "readouts", ()))
        tissues = _as_tuple(getattr(signals, "tissues", ()))
        risks = _as_tuple(getattr(signals, "safety_risks", ()))
        contribution = []
        if models:
            contribution.append("模型证据：" + "、".join(models))
        if readouts:
            contribution.append("readout：" + "、".join(readouts))
        if tissues:
            contribution.append("组织适配：" + "、".join(tissues))
        if risks:
            contribution.append("安全扣分：" + "、".join(risks))
        if not contribution:
            contribution.append("仅提供背景/综述线索")
        rows.append(
            {
                "pmid": str(getattr(paper, "pmid", "")),
                "year": int(getattr(paper, "year", 0) or 0),
                "title": str(getattr(paper, "title", "")),
                "evidence_score": round(evidence_score, 3),
                "contribution": "；".join(contribution),
            }
        )
    return sorted(rows, key=lambda row: (-float(row["evidence_score"]), -int(row["year"]), str(row["pmid"])))


def design_validation_experiment(score: ReprogrammingFactorScore) -> dict[str, object]:
    """Generate a practical, non-protocol validation design summary."""

    primary_tissue = score.target_tissues[0] if score.target_tissues else "target_cells"
    safety_flag = "high_risk" if score.safety_score < 0.35 else "gated" if score.safety_score < 0.55 else "standard_gated"
    delivery = "短暂 mRNA 或可关闭表达系统" if "transcription_factor" in score.modality else "小分子/基因调控轴递送方案"
    if "AAV" in score.modality.upper():
        delivery = "局部 AAV，需表达开关和剂量窗口"
    return {
        "objective": f"验证 {score.name} 是否能让老化 {primary_tissue} 恢复年轻状态，同时保留细胞身份。",
        "model": f"年轻 vs 老年 {primary_tissue} 细胞/类器官；优先体外，体内只作为后续阶段。",
        "arms": (
            "年轻对照",
            "老年未处理",
            f"老年 + {score.name}",
            "递送载体/溶剂对照",
            "高风险阳性基准" if safety_flag == "high_risk" else "低剂量/短时程安全窗口",
        ),
        "timepoints": ("早期表达窗口", "短期恢复窗口", "撤药/关闭后稳定窗口"),
        "efficacy_readouts": (
            "RNA-seq 或 qPCR 老化 signature 逆转",
            "DNA 甲基化年龄/表观年龄",
            "线粒体和应激相关功能 readout",
            "细胞类型身份标志物保持",
        ),
        "safety_readouts": (
            "MYC/NANOG/POU5F1 等多能性/增殖风险标志",
            "p16/p21、Ki67/EdU、DNA 损伤和凋亡",
            "炎症/免疫反应信号",
            "异常克隆扩增或去分化迹象",
        ),
        "decision_gate": _validation_gate(score),
        "delivery_note": delivery,
    }


def explain_reprogramming_score(
    score: ReprogrammingFactorScore,
    component_weights: Mapping[str, float] | None = None,
) -> list[str]:
    """Return a concise, human-readable scoring trace."""

    weights = _validated_weights(component_weights or DEFAULT_REPROGRAMMING_WEIGHTS)
    weighted = {
        key: score.components.get(key, 0.0) * weights[key]
        for key in weights
    }
    strongest = sorted(weighted.items(), key=lambda item: -item[1])[:3]
    weakest = sorted(weighted.items(), key=lambda item: item[1])[:3]
    notes = [
        f"总优先级 = Σ(组件分 × 权重)，当前为 {score.priority_score:.2f}；安全分为 {score.safety_score:.2f}。",
        "主要加分项：" + "；".join(
            f"{COMPONENT_LABELS[key]} {score.components.get(key, 0.0):.2f} × {weights[key]:.2f}"
            for key, _ in strongest
        ),
        "主要限制项：" + "；".join(
            f"{COMPONENT_LABELS[key]} {score.components.get(key, 0.0):.2f}"
            for key, _ in weakest
        ),
    ]
    if score.evidence_basis == "literature_adjusted":
        notes.append(f"本地文献动态调整：匹配 {score.literature_count} 篇论文，已影响证据强度、组织适配和安全风险。")
    else:
        notes.append("当前为基础评分：尚未找到足够本地文献触发动态调整。")
    if score.safety_warnings:
        notes.append("安全扣分来源：" + "；".join(score.safety_warnings))
    if score.safety_score < 0.35:
        notes.append("安全闸门：安全分低于 0.35，建议只作为高风险基准或阴性对照。")
    elif score.safety_score < 0.55:
        notes.append("安全闸门：需要短暂表达、局部递送、增殖/去分化监控后再进入验证。")
    else:
        notes.append("安全闸门：可进入聚焦验证，但仍需监控癌症、身份漂移和递送反应。")
    return notes


def suggest_reprogramming_next_steps(score: ReprogrammingFactorScore) -> list[str]:
    """Suggest practical next validation steps for a factor."""

    steps = []
    tissues = "、".join(score.target_tissues[:3]) if score.target_tissues else "目标细胞"
    if score.safety_score < 0.35:
        steps.append("先做文献复核和风险基准，不建议直接设计体内验证。")
        steps.append("重点整理癌症、畸胎瘤、去分化和异常增殖证据。")
    else:
        steps.append(f"优先选择 {tissues} 的体外模型，比较年轻/老年细胞状态。")
        steps.append("最小 readout：RNA-seq/qPCR、DNA甲基化年龄、细胞身份标志、p16/p21、Ki67/EdU。")
        steps.append("安全 readout：MYC/NANOG/POU5F1、异常增殖、DNA损伤、凋亡和炎症信号。")
    if score.components.get("evidence_strength", 0.0) < 0.55:
        steps.append("先用文献雷达补齐该因子的 PubMed 证据，再更新动态评分。")
    if score.components.get("delivery_feasibility", 0.0) < 0.55:
        steps.append("递送是短板：优先比较 mRNA、AAV、LNP 或小分子调控的可控性。")
    if score.components.get("identity_preservation", 0.0) < 0.55:
        steps.append("身份保留是短板：必须设置细胞类型标志物和多能性标志物双重监控。")
    return steps


def _validation_gate(score: ReprogrammingFactorScore) -> str:
    if score.safety_score < 0.35:
        return "只有在风险标志不上升且身份标志稳定时，才允许从高风险基准转入候选验证。"
    if score.safety_score < 0.55:
        return "进入下一步前必须同时满足年轻化 readout 改善、身份保留、多能性/异常增殖无明显上升。"
    return "若年轻化 readout 改善且安全 readout 稳定，可进入更复杂组织模型或局部递送验证。"


def _localized_recommendation(value: str) -> str:
    return {
        "prioritize focused validation": "优先做聚焦验证",
        "watchlist with safety gates": "观察名单，需安全闸门",
        "benchmark only; high-risk": "仅作高风险基准",
        "hold for mechanism review": "暂缓，先复核机制",
    }.get(value, value)


def _make_combination(
    *,
    combination_id: str,
    name: str,
    factors: tuple[ReprogrammingFactorScore, ...],
    target_tissue: str,
    risk_profile: str,
    strategy: str,
    rationale: tuple[str, ...],
    excluded_factors: tuple[str, ...],
    validation_plan: tuple[str, ...],
) -> ReprogrammingCombination:
    safety = min((factor.safety_score for factor in factors), default=0.0)
    priority = sum(factor.priority_score for factor in factors) / len(factors) if factors else 0.0
    synergy_bonus = min(0.08, 0.025 * max(0, len(factors) - 1))
    if any(factor.factor_id in {"oskm", "myc"} for factor in factors):
        synergy_bonus = -0.12
    if any(factor.factor_id == "osk" for factor in factors):
        synergy_bonus -= 0.03
    if risk_profile == "conservative" and safety < 0.55:
        synergy_bonus -= 0.08
    return ReprogrammingCombination(
        combination_id=combination_id,
        name=name,
        factor_ids=tuple(factor.factor_id for factor in factors),
        factor_names=tuple(factor.name for factor in factors),
        target_tissue=target_tissue,
        risk_profile=risk_profile,
        strategy=strategy,
        priority_score=round(_clamp(priority + synergy_bonus), 6),
        safety_score=round(safety, 6),
        rationale=rationale,
        excluded_factors=excluded_factors,
        validation_plan=validation_plan,
    )


def _combination_validation_plan(
    factors: tuple[ReprogrammingFactorScore, ...],
    target_tissue: str,
    mode: str,
) -> tuple[str, ...]:
    names = " + ".join(factor.name for factor in factors)
    base = [
        f"在年轻/老年 {target_tissue} 体外模型中先做分步验证：单因子、两两组合、完整组合。",
        "所有组合必须比较年轻化 signature、DNA 甲基化年龄、细胞身份标志和功能 readout。",
        "安全闸门固定包括 MYC/NANOG/POU5F1、p16/p21、Ki67/EdU、DNA 损伤、凋亡和炎症信号。",
    ]
    if mode == "low_risk":
        base.append(f"{names} 若只能轻度改善表观年龄，也可作为后续 OSK 方案的安全辅助层。")
    elif mode == "gated_osk":
        base.append("OSK 组合只允许短暂、可关闭表达；撤除后仍需观察年轻化状态是否稳定。")
        base.append("若身份标志下降或多能性/增殖标志上升，组合直接判为 No-Go。")
    else:
        base.append("该组合只用于建立风险上限，不进入候选治疗路线。")
    return tuple(base)


def _localized_risk_profile(value: str) -> str:
    return {
        "conservative": "保守",
        "balanced": "平衡",
        "benchmark_only": "仅基准",
    }.get(value, value)


def _tissue_family_match(tissue: str, tissues: tuple[str, ...]) -> bool:
    families = {
        "immune": {"immune", "hematopoietic"},
        "neuron": {"neuron", "brain"},
        "muscle": {"muscle", "regeneration"},
        "fibroblast": {"fibroblast", "skin"},
        "retina": {"retina", "neuron"},
    }
    return bool(families.get(tissue, {tissue}).intersection(tissues))


def _best_combo_for_tissue(
    combinations: list[ReprogrammingCombination],
    tissue: str,
) -> ReprogrammingCombination | None:
    tissue_combos = [
        combo
        for combo in combinations
        if combo.target_tissue == tissue or combo.target_tissue == "fibroblast"
    ]
    if not tissue_combos:
        tissue_combos = combinations
    return max(tissue_combos, key=lambda combo: (combo.priority_score, combo.safety_score), default=None)


def _tissue_profile(tissue: str) -> dict[str, object]:
    profiles: dict[str, dict[str, object]] = {
        "fibroblast": {
            "label": "皮肤/成纤维细胞",
            "model": "年轻/老年人源成纤维细胞；可扩展到皮肤类器官或伤口愈合模型",
            "delivery": "短暂 mRNA、小分子调控或可关闭表达系统；先避开全身递送",
            "readouts": ("表观年龄", "胶原/ECM 重塑", "细胞身份标志", "应激恢复"),
            "safety": ("多能性标志", "异常增殖", "DNA 损伤", "衰老相关炎症"),
        },
        "retina": {
            "label": "视网膜/视神经",
            "model": "视网膜神经节细胞、视网膜类器官；后续才考虑局部动物模型",
            "delivery": "局部递送和可控表达优先；AAV 类方案必须绑定表达开关",
            "readouts": ("神经功能", "轴突再生/存活", "表观年龄", "细胞身份标志"),
            "safety": ("炎症反应", "视网膜结构异常", "多能性标志", "异常增殖"),
        },
        "muscle": {
            "label": "肌肉/再生",
            "model": "肌管、肌卫星细胞或肌肉类器官；关注肌少症相关功能 readout",
            "delivery": "局部 mRNA/LNP 或短时程表达；优先避免长期转录因子表达",
            "readouts": ("肌生成标志", "收缩/代谢功能", "线粒体状态", "表观年龄"),
            "safety": ("纤维化", "异常增殖", "身份漂移", "炎症"),
        },
        "immune": {
            "label": "免疫/造血",
            "model": "外周免疫细胞、造血祖细胞；先做 ex vivo 状态恢复",
            "delivery": "ex vivo 编辑或可逆表观调控优先；体内递送风险较高",
            "readouts": ("免疫功能", "炎症谱", "克隆扩增", "表观年龄"),
            "safety": ("克隆性造血", "肿瘤相关通路", "炎症风暴", "分化偏移"),
        },
        "neuron": {
            "label": "神经/脑",
            "model": "神经元、胶质细胞或脑类器官；先做体外年龄状态逆转",
            "delivery": "局部/细胞类型特异递送，必须限制表达窗口",
            "readouts": ("突触/应激功能", "线粒体状态", "表观年龄", "神经身份标志"),
            "safety": ("身份漂移", "兴奋毒性", "炎症", "异常增殖"),
        },
    }
    return profiles.get(tissue, profiles["fibroblast"])


def _tissue_next_actions(
    tissue: str,
    lead_scores: list[ReprogrammingFactorScore],
    lead_combo: ReprogrammingCombination | None,
) -> tuple[str, ...]:
    lead = "、".join(score.name for score in lead_scores[:3]) or "候选因子"
    combo = lead_combo.name if lead_combo else "低风险组合"
    return (
        f"先围绕 {lead} 建立 {tissue} 年轻/老年状态分类器。",
        f"用 {combo} 做第一轮组合对照，记录年轻化、身份保留和安全 readout。",
        "把结果回填到本地评分：年轻化不伴随身份漂移才允许进入下一轮。",
    )


def _localized_gate(level: str) -> str:
    return {"red": "红灯", "amber": "黄灯", "green": "绿灯"}[level]


def _must_pass_readouts(level: str) -> tuple[str, ...]:
    common = (
        "年轻化 signature 改善",
        "细胞身份标志不下降",
        "DNA 损伤不升高",
    )
    if level == "red":
        return common + ("多能性/异常增殖标志不升高", "只允许作为风险基准")
    if level == "amber":
        return common + ("撤除后状态稳定", "表达窗口可关闭")
    return common + ("功能 readout 改善", "炎症信号不升高")


def _stop_triggers(level: str) -> tuple[str, ...]:
    triggers = (
        "NANOG/POU5F1/MYC 等风险标志持续升高",
        "Ki67/EdU 异常升高或克隆扩增",
        "细胞类型身份标志明显下降",
    )
    if level == "red":
        return triggers + ("任何去分化迹象均停止候选推进",)
    if level == "amber":
        return triggers + ("撤除后风险 readout 未恢复即停止",)
    return triggers + ("功能改善不足且安全负担增加即降级",)


def _gap_urgency(score: ReprogrammingFactorScore, gaps: list[str]) -> float:
    urgency = 0.25 + 0.12 * len(gaps)
    if score.priority_score >= 0.6:
        urgency += 0.18
    if score.safety_score < 0.55:
        urgency += 0.15
    if score.literature_count == 0:
        urgency += 0.12
    return round(_clamp(urgency), 6)


def _gap_query(score: ReprogrammingFactorScore) -> str:
    tissue = " OR ".join(score.target_tissues[:3]) if score.target_tissues else "aging"
    return f'("{score.name}" OR {score.factor_id}) partial reprogramming aging ({tissue}) safety'


def _gap_ai_task(score: ReprogrammingFactorScore, gaps: list[str]) -> str:
    return (
        f"AI 检索并结构化 {score.name} 的部分重编程证据，重点回答："
        f"{'、'.join(gaps[:3])}；输出模型、组织、readout、安全风险和可复现实验边界。"
    )


def _read_rows(path: str | Path, required_columns: tuple[str, ...]) -> list[dict[str, str]]:
    csv_path = Path(path)
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in required_columns if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{csv_path} is missing required columns: {', '.join(missing)}")
        return list(reader)


def _required(row: dict[str, str], field: str) -> str:
    value = row.get(field, "").strip()
    if not value:
        raise ValueError(f"Field {field!r} is required")
    return value


def _bounded_float(row: dict[str, str], field: str) -> float:
    raw_value = _required(row, field)
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ValueError(f"Field {field!r} must be a float") from exc
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"Field {field!r} must be between 0.0 and 1.0")
    return value


def _split_ids(value: str) -> tuple[str, ...]:
    ids = tuple(part.strip() for part in value.split(";") if part.strip())
    if not ids:
        raise ValueError("Field 'target_tissues' must contain at least one tissue ID")
    return ids


def _split_optional_ids(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(";") if part.strip())


def _ensure_unique(field: str, values: list[str]) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"Duplicate {field} values are not allowed")


def _validated_weights(weights: Mapping[str, float]) -> dict[str, float]:
    expected = set(DEFAULT_REPROGRAMMING_WEIGHTS)
    actual = set(weights)
    if actual != expected:
        missing = expected - actual
        extra = actual - expected
        details = []
        if missing:
            details.append(f"missing: {', '.join(sorted(missing))}")
        if extra:
            details.append(f"extra: {', '.join(sorted(extra))}")
        raise ValueError(f"Component weights must match reprogramming components ({'; '.join(details)})")
    normalized = {name: float(value) for name, value in weights.items()}
    if any(value < 0.0 for value in normalized.values()):
        raise ValueError("Component weights must be non-negative")
    if sum(normalized.values()) <= 0.0:
        raise ValueError("At least one component weight must be positive")
    return normalized


def _signal_value(paper: object, field: str) -> float:
    signals = getattr(paper, "signals", None)
    value = getattr(signals, field, 0.0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _signal_tuple(paper: object, field: str) -> tuple[str, ...]:
    signals = getattr(paper, "signals", None)
    value = getattr(signals, field, ())
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return ()


def _as_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, tuple):
        return tuple(str(item) for item in value)
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    if value:
        return (str(value),)
    return ()


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))
