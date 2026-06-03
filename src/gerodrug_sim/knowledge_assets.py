"""Knowledge assets and gene scoring for the reprogramming cockpit."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, Mapping


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GENES = ROOT / "data" / "candidate_genes.csv"
DEFAULT_ORGANIZATIONS = ROOT / "data" / "research_organizations.csv"


GENE_COLUMNS = (
    "gene_id",
    "symbol",
    "aliases",
    "category",
    "mechanism",
    "target_tissues",
    "rejuvenation_potential",
    "identity_preservation",
    "oncogenic_risk",
    "dedifferentiation_risk",
    "delivery_feasibility",
    "tissue_specificity",
    "evidence_strength",
    "druggability",
    "reprogramming_relevance",
    "notes",
    "evidence_query",
)


ORGANIZATION_COLUMNS = (
    "org_id",
    "name",
    "org_type",
    "country",
    "city",
    "focus",
    "tags",
    "url",
    "notes",
)


GENE_SCORE_WEIGHTS = {
    "rejuvenation_potential": 0.22,
    "identity_preservation": 0.14,
    "safety": 0.22,
    "delivery_feasibility": 0.10,
    "tissue_specificity": 0.08,
    "evidence_strength": 0.12,
    "druggability": 0.05,
    "reprogramming_relevance": 0.07,
}


GENE_WEIGHT_SCENARIOS = {
    "balanced": GENE_SCORE_WEIGHTS,
    "safety_first": {
        "rejuvenation_potential": 0.14,
        "identity_preservation": 0.18,
        "safety": 0.34,
        "delivery_feasibility": 0.10,
        "tissue_specificity": 0.07,
        "evidence_strength": 0.11,
        "druggability": 0.03,
        "reprogramming_relevance": 0.03,
    },
    "rejuvenation_first": {
        "rejuvenation_potential": 0.34,
        "identity_preservation": 0.10,
        "safety": 0.14,
        "delivery_feasibility": 0.08,
        "tissue_specificity": 0.08,
        "evidence_strength": 0.10,
        "druggability": 0.04,
        "reprogramming_relevance": 0.12,
    },
    "evidence_first": {
        "rejuvenation_potential": 0.18,
        "identity_preservation": 0.12,
        "safety": 0.18,
        "delivery_feasibility": 0.08,
        "tissue_specificity": 0.08,
        "evidence_strength": 0.26,
        "druggability": 0.04,
        "reprogramming_relevance": 0.06,
    },
}


@dataclass(frozen=True)
class CandidateGene:
    """A gene-level candidate for partial reprogramming or safety support."""

    gene_id: str
    symbol: str
    aliases: tuple[str, ...]
    category: str
    mechanism: str
    target_tissues: tuple[str, ...]
    rejuvenation_potential: float
    identity_preservation: float
    oncogenic_risk: float
    dedifferentiation_risk: float
    delivery_feasibility: float
    tissue_specificity: float
    evidence_strength: float
    druggability: float
    reprogramming_relevance: float
    notes: str = ""
    evidence_query: str = ""


@dataclass(frozen=True)
class ResearchOrganization:
    """A company, institute, or lab relevant to longevity/reprogramming."""

    org_id: str
    name: str
    org_type: str
    country: str
    city: str
    focus: str
    tags: tuple[str, ...]
    url: str
    notes: str = ""


@dataclass(frozen=True)
class GeneScore:
    """A traceable score for an arbitrary gene query."""

    query: str
    gene_id: str
    symbol: str
    matched: bool
    total_score: float
    rejuvenation_potential: float
    risk_score: float
    safety_score: float
    components: dict[str, float]
    risk_band: str
    recommendation: str
    mechanism: str
    target_tissues: tuple[str, ...]
    evidence_query: str
    warnings: tuple[str, ...] = ()
    evidence_basis: str = "curated_seed"
    literature_count: int = 0
    evidence_pmids: tuple[str, ...] = ()
    provenance_score: float = 0.0
    audit_notes: tuple[str, ...] = ()


def load_candidate_genes(path: str | Path = DEFAULT_GENES) -> list[CandidateGene]:
    """Load candidate genes from CSV."""

    rows = _read_rows(path, GENE_COLUMNS)
    genes = [
        CandidateGene(
            gene_id=_required(row, "gene_id"),
            symbol=_required(row, "symbol").upper(),
            aliases=_split_optional(row.get("aliases", "")),
            category=_required(row, "category"),
            mechanism=_required(row, "mechanism"),
            target_tissues=_split_required(row.get("target_tissues", "")),
            rejuvenation_potential=_bounded_float(row, "rejuvenation_potential"),
            identity_preservation=_bounded_float(row, "identity_preservation"),
            oncogenic_risk=_bounded_float(row, "oncogenic_risk"),
            dedifferentiation_risk=_bounded_float(row, "dedifferentiation_risk"),
            delivery_feasibility=_bounded_float(row, "delivery_feasibility"),
            tissue_specificity=_bounded_float(row, "tissue_specificity"),
            evidence_strength=_bounded_float(row, "evidence_strength"),
            druggability=_bounded_float(row, "druggability"),
            reprogramming_relevance=_bounded_float(row, "reprogramming_relevance"),
            notes=row.get("notes", "").strip(),
            evidence_query=row.get("evidence_query", "").strip(),
        )
        for row in rows
    ]
    _ensure_unique("gene_id", [gene.gene_id for gene in genes])
    _ensure_unique("symbol", [gene.symbol for gene in genes])
    return genes


def load_research_organizations(path: str | Path = DEFAULT_ORGANIZATIONS) -> list[ResearchOrganization]:
    """Load the company/lab/institute landscape from CSV."""

    rows = _read_rows(path, ORGANIZATION_COLUMNS)
    organizations = [
        ResearchOrganization(
            org_id=_required(row, "org_id"),
            name=_required(row, "name"),
            org_type=_required(row, "org_type"),
            country=_required(row, "country"),
            city=_required(row, "city"),
            focus=_required(row, "focus"),
            tags=_split_optional(row.get("tags", "")),
            url=_required(row, "url"),
            notes=row.get("notes", "").strip(),
        )
        for row in rows
    ]
    _ensure_unique("org_id", [organization.org_id for organization in organizations])
    return organizations


def score_gene_candidate(
    gene: CandidateGene,
    query: str | None = None,
    weights: Mapping[str, float] | None = None,
) -> GeneScore:
    """Score a known gene for partial-reprogramming R&D priority."""

    normalized_weights = _validated_weights(weights or GENE_SCORE_WEIGHTS)
    safety_score = gene_safety_score(gene)
    risk_score = round(1.0 - safety_score, 6)
    components = {
        "rejuvenation_potential": gene.rejuvenation_potential,
        "identity_preservation": gene.identity_preservation,
        "safety": safety_score,
        "delivery_feasibility": gene.delivery_feasibility,
        "tissue_specificity": gene.tissue_specificity,
        "evidence_strength": gene.evidence_strength,
        "druggability": gene.druggability,
        "reprogramming_relevance": gene.reprogramming_relevance,
    }
    total = sum(components[name] * normalized_weights[name] for name in normalized_weights) / sum(normalized_weights.values())
    risk_band = _risk_band(gene, safety_score)
    return GeneScore(
        query=(query or gene.symbol).strip(),
        gene_id=gene.gene_id,
        symbol=gene.symbol,
        matched=True,
        total_score=round(total, 6),
        rejuvenation_potential=round(gene.rejuvenation_potential, 6),
        risk_score=risk_score,
        safety_score=round(safety_score, 6),
        components={key: round(value, 6) for key, value in components.items()},
        risk_band=risk_band,
        recommendation=_gene_recommendation(total, safety_score, gene.evidence_strength),
        mechanism=gene.mechanism,
        target_tissues=gene.target_tissues,
        evidence_query=gene.evidence_query or _default_gene_query(gene.symbol, gene.target_tissues),
        warnings=_gene_warnings(gene, safety_score),
        evidence_basis="curated_seed",
        literature_count=0,
        evidence_pmids=(),
        provenance_score=round(gene.evidence_strength * 0.55 + 0.15, 6),
        audit_notes=("CSV curated prior; no local literature adjustment applied",),
    )


def score_gene_candidate_with_literature(
    gene: CandidateGene,
    papers: Iterable[object],
    query: str | None = None,
    weights: Mapping[str, float] | None = None,
) -> GeneScore:
    """Score a gene after using local papers as an evidence/provenance layer."""

    matched_papers = papers_for_gene(gene, papers)
    if not matched_papers:
        return score_gene_candidate(gene, query=query, weights=weights)
    evidence_scores = [_paper_evidence_score(paper) for paper in matched_papers]
    average_evidence = sum(evidence_scores) / len(evidence_scores)
    risks = {
        risk
        for paper in matched_papers
        for risk in _paper_signal_tuple(paper, "safety_risks")
    }
    functional_count = sum(1 for paper in matched_papers if "function" in _paper_signal_tuple(paper, "readouts"))
    tissue_count = len({tissue for paper in matched_papers for tissue in _paper_signal_tuple(paper, "tissues")})
    adjusted = CandidateGene(
        gene_id=gene.gene_id,
        symbol=gene.symbol,
        aliases=gene.aliases,
        category=gene.category,
        mechanism=gene.mechanism,
        target_tissues=gene.target_tissues,
        rejuvenation_potential=_clamp(gene.rejuvenation_potential + min(0.06, 0.012 * functional_count)),
        identity_preservation=gene.identity_preservation,
        oncogenic_risk=_clamp(gene.oncogenic_risk + (0.04 if "oncogenic risk" in risks else 0.0)),
        dedifferentiation_risk=_clamp(gene.dedifferentiation_risk + (0.04 if "dedifferentiation" in risks else 0.0)),
        delivery_feasibility=gene.delivery_feasibility,
        tissue_specificity=_clamp(gene.tissue_specificity + min(0.08, 0.018 * tissue_count)),
        evidence_strength=_clamp(gene.evidence_strength * 0.55 + average_evidence * 0.45 + min(0.10, 0.01 * len(matched_papers))),
        druggability=gene.druggability,
        reprogramming_relevance=gene.reprogramming_relevance,
        notes=gene.notes,
        evidence_query=gene.evidence_query,
    )
    score = score_gene_candidate(adjusted, query=query or gene.symbol, weights=weights)
    provenance = _clamp(0.35 + min(0.35, 0.035 * len(matched_papers)) + average_evidence * 0.30)
    warnings = tuple(sorted(set(score.warnings + tuple(risks))))
    return GeneScore(
        query=score.query,
        gene_id=score.gene_id,
        symbol=score.symbol,
        matched=score.matched,
        total_score=score.total_score,
        rejuvenation_potential=score.rejuvenation_potential,
        risk_score=score.risk_score,
        safety_score=score.safety_score,
        components=score.components,
        risk_band=score.risk_band,
        recommendation=score.recommendation,
        mechanism=score.mechanism,
        target_tissues=score.target_tissues,
        evidence_query=score.evidence_query,
        warnings=warnings,
        evidence_basis="literature_adjusted",
        literature_count=len(matched_papers),
        evidence_pmids=tuple(str(getattr(paper, "pmid", "")) for paper in matched_papers[:8]),
        provenance_score=round(provenance, 6),
        audit_notes=(
            f"Matched {len(matched_papers)} local PubMed records by symbol/alias text",
            "Literature adjusted evidence strength, tissue specificity, functional readout bonus, and safety penalties",
        ),
    )


def score_gene_query(query: str, genes: Iterable[CandidateGene] | None = None) -> GeneScore:
    """Score an arbitrary gene symbol or alias."""

    cleaned = query.strip().upper()
    if not cleaned:
        raise ValueError("Gene query is required")
    gene_list = list(genes) if genes is not None else load_candidate_genes()
    matched = find_gene(cleaned, gene_list)
    if matched:
        return score_gene_candidate(matched, query=query)
    inferred = CandidateGene(
        gene_id=f"unknown_{cleaned.lower()}",
        symbol=cleaned,
        aliases=(),
        category="unknown",
        mechanism="Uncurated gene. Treat as an evidence discovery target before any wet-lab prioritization.",
        target_tissues=("unknown",),
        rejuvenation_potential=0.35,
        identity_preservation=0.50,
        oncogenic_risk=0.50,
        dedifferentiation_risk=0.45,
        delivery_feasibility=0.45,
        tissue_specificity=0.30,
        evidence_strength=0.15,
        druggability=0.30,
        reprogramming_relevance=0.25,
        notes="No curated row yet. Use the generated literature task first.",
        evidence_query=_default_gene_query(cleaned, ("aging",)),
    )
    score = score_gene_candidate(inferred, query=query)
    return GeneScore(
        query=score.query,
        gene_id=score.gene_id,
        symbol=score.symbol,
        matched=False,
        total_score=score.total_score,
        rejuvenation_potential=score.rejuvenation_potential,
        risk_score=score.risk_score,
        safety_score=score.safety_score,
        components=score.components,
        risk_band="unknown",
        recommendation="先补文献证据，不进入候选优先级",
        mechanism=score.mechanism,
        target_tissues=score.target_tissues,
        evidence_query=score.evidence_query,
        warnings=("未命中本地候选基因库", "需要先做 PubMed/数据库证据抽取"),
        evidence_basis="unknown_query",
        literature_count=0,
        evidence_pmids=(),
        provenance_score=0.05,
        audit_notes=("No local curated gene row matched the query",),
    )


def score_gene_query_with_literature(
    query: str,
    genes: Iterable[CandidateGene] | None = None,
    papers: Iterable[object] = (),
) -> GeneScore:
    """Score an arbitrary gene query using curated priors plus local literature."""

    cleaned = query.strip().upper()
    gene_list = list(genes) if genes is not None else load_candidate_genes()
    matched = find_gene(cleaned, gene_list)
    if matched:
        return score_gene_candidate_with_literature(matched, papers, query=query)
    return score_gene_query(query, gene_list)


def rank_candidate_genes(genes: Iterable[CandidateGene]) -> list[GeneScore]:
    """Rank all curated genes by total score and safety."""

    scores = [score_gene_candidate(gene) for gene in genes]
    return sorted(scores, key=lambda score: (-score.total_score, -score.safety_score, score.symbol))


def rank_candidate_genes_with_literature(
    genes: Iterable[CandidateGene],
    papers: Iterable[object],
) -> list[GeneScore]:
    """Rank genes using curated priors plus local-paper provenance."""

    paper_list = list(papers)
    scores = [score_gene_candidate_with_literature(gene, paper_list) for gene in genes]
    return sorted(scores, key=lambda score: (-score.total_score, -score.provenance_score, -score.safety_score, score.symbol))


def stress_test_gene_candidate(
    gene: CandidateGene,
    papers: Iterable[object],
    scenarios: Mapping[str, Mapping[str, float]] | None = None,
) -> dict[str, object]:
    """Test whether a gene remains attractive under different scoring weights."""

    scenario_map = scenarios or GENE_WEIGHT_SCENARIOS
    paper_list = list(papers)
    scenario_rows = []
    for name, weights in scenario_map.items():
        score = score_gene_candidate_with_literature(gene, paper_list, weights=weights)
        scenario_rows.append(
            {
                "scenario": name,
                "score": score.total_score,
                "safety": score.safety_score,
                "risk": score.risk_score,
                "recommendation": score.recommendation,
                "provenance": score.provenance_score,
            }
        )
    scores = [float(row["score"]) for row in scenario_rows]
    spread = max(scores) - min(scores) if scores else 0.0
    average = sum(scores) / len(scores) if scores else 0.0
    return {
        "symbol": gene.symbol,
        "scenario_scores": scenario_rows,
        "min_score": round(min(scores), 6) if scores else 0.0,
        "max_score": round(max(scores), 6) if scores else 0.0,
        "average_score": round(average, 6),
        "spread": round(spread, 6),
        "stability": _stability_label(spread),
        "decision": _stress_decision(average, spread, min(row["safety"] for row in scenario_rows)),
    }


def stress_test_report_rows(
    genes: Iterable[CandidateGene],
    papers: Iterable[object],
    limit: int = 30,
) -> list[dict[str, object]]:
    """Build sorted stress-test rows for GUI/reporting."""

    paper_list = list(papers)
    rows = [stress_test_gene_candidate(gene, paper_list) for gene in genes]
    return sorted(
        rows,
        key=lambda row: (
            str(row["stability"]) != "稳定",
            -float(row["average_score"]),
            float(row["spread"]),
            str(row["symbol"]),
        ),
    )[:limit]


def build_gene_evidence_pack(gene: CandidateGene, papers: Iterable[object]) -> dict[str, object]:
    """Create a compact evidence packet for a gene."""

    matched = papers_for_gene(gene, papers)
    readouts = sorted({readout for paper in matched for readout in _paper_signal_tuple(paper, "readouts")})
    tissues = sorted({tissue for paper in matched for tissue in _paper_signal_tuple(paper, "tissues")})
    risks = sorted({risk for paper in matched for risk in _paper_signal_tuple(paper, "safety_risks")})
    models = sorted({model for paper in matched for model in _paper_signal_tuple(paper, "models")})
    average_score = sum(_paper_evidence_score(paper) for paper in matched) / len(matched) if matched else 0.0
    top_papers = [
        {
            "pmid": str(getattr(paper, "pmid", "")),
            "year": int(getattr(paper, "year", 0) or 0),
            "title": str(getattr(paper, "title", "")),
            "evidence_score": round(_paper_evidence_score(paper), 6),
            "contribution": _paper_contribution(paper),
        }
        for paper in matched[:8]
    ]
    gaps = []
    if len(matched) < 3:
        gaps.append("PMID 命中文献不足")
    if not readouts:
        gaps.append("缺少明确 readout")
    if not tissues:
        gaps.append("缺少组织/细胞模型信息")
    if gene.oncogenic_risk >= 0.60 and "oncogenic risk" not in risks:
        gaps.append("高风险基因缺少癌变风险文献归因")
    if not gaps:
        gaps.append("可进入人工证据复核")
    return {
        "symbol": gene.symbol,
        "gene_id": gene.gene_id,
        "paper_count": len(matched),
        "average_evidence_score": round(average_score, 6),
        "readouts": readouts,
        "tissues": tissues,
        "models": models,
        "safety_risks": risks,
        "top_papers": top_papers,
        "gaps": gaps,
        "evidence_query": gene.evidence_query or _default_gene_query(gene.symbol, gene.target_tissues),
        "summary": _evidence_pack_summary(gene, len(matched), average_score, risks),
    }


def build_gene_evidence_packs(
    genes: Iterable[CandidateGene],
    papers: Iterable[object],
    limit: int = 20,
) -> list[dict[str, object]]:
    """Build evidence packets and sort by literature support."""

    paper_list = list(papers)
    packs = [build_gene_evidence_pack(gene, paper_list) for gene in genes]
    return sorted(
        packs,
        key=lambda pack: (-int(pack["paper_count"]), -float(pack["average_evidence_score"]), str(pack["symbol"])),
    )[:limit]


def build_gene_portfolio(scores: Iterable[GeneScore]) -> list[dict[str, object]]:
    """Classify scored genes into an actionable research portfolio."""

    rows = []
    for score in scores:
        if score.risk_band == "high" or score.safety_score < 0.40:
            bucket = "风险基准"
            action = "只作为安全模型和反例，不直接推进"
        elif score.total_score >= 0.64 and score.safety_score >= 0.55 and score.provenance_score >= 0.45 and score.literature_count >= 3:
            bucket = "核心候选"
            action = "进入证据包复核和体外 readout 设计"
        elif score.total_score >= 0.56 and (score.provenance_score < 0.45 or score.literature_count < 3):
            bucket = "补证据候选"
            action = "先补 PMID 级证据和组织 readout"
        elif score.safety_score >= 0.70 and score.rejuvenation_potential >= 0.45:
            bucket = "安全辅助轴"
            action = "可作为 OSK/低风险组合的支持因子"
        else:
            bucket = "观察池"
            action = "保留在数据库，等待新证据触发重评分"
        rows.append(
            {
                "symbol": score.symbol,
                "bucket": bucket,
                "score": score.total_score,
                "safety": score.safety_score,
                "risk": score.risk_score,
                "provenance": score.provenance_score,
                "literature_count": score.literature_count,
                "action": action,
                "reason": _portfolio_reason(score),
            }
        )
    bucket_order = {"核心候选": 0, "安全辅助轴": 1, "补证据候选": 2, "风险基准": 3, "观察池": 4}
    return sorted(rows, key=lambda row: (bucket_order[str(row["bucket"])], -float(row["score"]), str(row["symbol"])))


def scoring_method_card() -> dict[str, object]:
    """Expose the scoring method as an auditable payload."""

    return {
        "method_version": "gene-score-v2-literature-stress",
        "formula": "total = weighted mean(rejuvenation, identity, safety, delivery, tissue, evidence, druggability, reprogramming relevance)",
        "base_weights": dict(GENE_SCORE_WEIGHTS),
        "stress_scenarios": {name: dict(weights) for name, weights in GENE_WEIGHT_SCENARIOS.items()},
        "literature_adjustment": (
            "Local PubMed matches adjust evidence strength, tissue specificity, functional readout bonus, "
            "oncogenic risk, dedifferentiation risk, and provenance score."
        ),
        "decision_boundary": "Scores are R&D prioritization signals, not biological proof or clinical claims.",
    }


def build_program_milestones(
    *,
    gene_portfolio: Iterable[Mapping[str, object]],
    evidence_packs: Iterable[Mapping[str, object]],
    audit: Mapping[str, object],
    tissue_plans: Iterable[Mapping[str, object]],
    safety_gates: Iterable[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Convert ranking outputs into a concrete stage-gated R&D plan."""

    portfolio = list(gene_portfolio)
    packs = list(evidence_packs)
    tissues = list(tissue_plans)
    gates = list(safety_gates)
    core = [row for row in portfolio if row.get("bucket") == "核心候选"]
    support = [row for row in portfolio if row.get("bucket") == "安全辅助轴"]
    evidence = [row for row in portfolio if row.get("bucket") == "补证据候选"]
    risk = [row for row in portfolio if row.get("bucket") == "风险基准"]
    lead_tissue = str(tissues[0].get("label", "fibroblast")) if tissues else "fibroblast"
    lead_candidates = _symbol_list(core or support or evidence, limit=4)
    weak_pack_count = sum(1 for pack in packs if int(pack.get("paper_count", 0)) < 3)
    credibility_grade = str(audit.get("credibility_grade", "C 仅原型"))
    gate_names = _symbol_list(gates, key="gate", limit=3) or "绿灯/黄灯/红灯"
    return [
        {
            "phase": "0-30 天",
            "objective": "把候选判断从分数升级为可复核证据包",
            "deliverable": f"完成 Top {min(20, len(portfolio))} 基因证据包人工复核，优先 {lead_candidates}",
            "success_metric": f"PMID、readout、组织、模型、安全风险字段齐全；低于 3 篇证据的候选 {weak_pack_count} 个被标记",
            "exit_gate": f"可信度等级不低于 {credibility_grade}，所有核心/辅助候选都有明确补证据动作",
            "owner_hint": "生物信息/文献复核",
        },
        {
            "phase": "31-60 天",
            "objective": "锁定第一条组织年轻化路线",
            "deliverable": f"围绕 {lead_tissue} 输出模型、递送、主要 readout 和安全 readout 的实验 brief",
            "success_metric": "每条 readout 都能对应到证据包或安全闸门，且有 Go/No-Go 阈值",
            "exit_gate": f"安全闸门覆盖 {gate_names}，高风险基因只留作反例/基准",
            "owner_hint": "转化生物学顾问",
        },
        {
            "phase": "61-90 天",
            "objective": "形成可给合作方/CRO 报价的验证包",
            "deliverable": "1 个局部组织 pilot、1 个阴性/风险基准、1 套表观年龄+功能+安全 readout 清单",
            "success_metric": f"核心候选 {len(core)} 个，安全辅助轴 {len(support)} 个，补证据候选 {len(evidence)} 个，风险基准 {len(risk)} 个",
            "exit_gate": "能够拿到至少 2 个外部实验报价或高校合作反馈",
            "owner_hint": "BD/外包实验协调",
        },
        {
            "phase": "3-6 个月",
            "objective": "把 AI 文献闭环升级为专有数据闭环",
            "deliverable": "接入外部实验结果、失败样本和专家复核意见，形成评分 diff 与模型卡",
            "success_metric": "每次新增证据都能追踪评分变化、候选分层变化和安全红旗变化",
            "exit_gate": "投资人能看到数据产生过程，而不是只看到静态名单",
            "owner_hint": "数据产品/研发负责人",
        },
    ]


def build_experiment_backlog(
    *,
    gene_portfolio: Iterable[Mapping[str, object]],
    evidence_packs: Iterable[Mapping[str, object]],
    tissue_plans: Iterable[Mapping[str, object]],
    safety_gates: Iterable[Mapping[str, object]],
    limit: int = 18,
) -> list[dict[str, object]]:
    """Generate an execution backlog from the current portfolio and evidence gaps."""

    portfolio = list(gene_portfolio)
    pack_index = {str(pack.get("symbol", "")): pack for pack in evidence_packs}
    rows: list[dict[str, object]] = []
    for row in portfolio[:12]:
        symbol = str(row.get("symbol", "-"))
        bucket = str(row.get("bucket", "观察池"))
        pack = pack_index.get(symbol, {})
        paper_count = int(pack.get("paper_count", row.get("literature_count", 0)) or 0)
        if bucket == "风险基准":
            lane = "安全反例"
            priority = "P1" if float(row.get("risk", 0.0)) >= 0.55 else "P2"
            deliverable = f"{symbol} 风险基准卡：只定义停止触发，不定义推进方案"
            success = "能解释为什么不推进，并能作为癌变/去分化风险对照"
            cost = "低"
        elif paper_count < 3 or bucket == "补证据候选":
            lane = "证据补强"
            priority = "P0"
            deliverable = f"{symbol} PMID 证据包补齐到至少 3 篇高相关论文"
            success = "至少包含组织、模型、readout、安全风险和失败边界"
            cost = "低"
        elif bucket in {"核心候选", "安全辅助轴"}:
            lane = "体外验证设计"
            priority = "P0" if bucket == "核心候选" else "P1"
            deliverable = f"{symbol} 体外验证 brief：模型、剂量/时程、表观年龄和功能 readout"
            success = "可直接发给合作实验室评估报价和可行性"
            cost = "中"
        else:
            lane = "观察池"
            priority = "P3"
            deliverable = f"{symbol} 自动监控检索式"
            success = "新增证据触发重评分即可"
            cost = "低"
        rows.append(
            {
                "task_id": f"GENE-{symbol}",
                "lane": lane,
                "priority": priority,
                "target": symbol,
                "deliverable": deliverable,
                "success_criteria": success,
                "dependency": "本地文献库/人工复核",
                "cost_band": cost,
                "status": "待执行",
            }
        )
    for index, plan in enumerate(list(tissue_plans)[:3], start=1):
        rows.append(
            {
                "task_id": f"TISSUE-{index:02d}",
                "lane": "组织路线",
                "priority": "P0" if index == 1 else "P1",
                "target": str(plan.get("label", "-")),
                "deliverable": f"{plan.get('label', '-')} 模型系统与递送路线 one-pager",
                "success_criteria": "模型、递送、主要 readout、安全重点和下一步动作齐全",
                "dependency": "组织路线图",
                "cost_band": "低",
                "status": "待执行",
            }
        )
    for index, gate in enumerate(list(safety_gates)[:3], start=1):
        rows.append(
            {
                "task_id": f"GATE-{index:02d}",
                "lane": "安全闸门",
                "priority": "P0",
                "target": str(gate.get("name", gate.get("gate", "-"))),
                "deliverable": f"{gate.get('gate', '安全闸门')} SOP：must-pass、stop-trigger、复核节奏",
                "success_criteria": "所有推进候选都能绑定至少一个停止触发条件",
                "dependency": "安全闸门矩阵",
                "cost_band": "低",
                "status": "待执行",
            }
        )
    return sorted(
        rows,
        key=lambda item: (
            _priority_rank(str(item["priority"])),
            _backlog_lane_rank(str(item["lane"])),
            str(item["task_id"]),
        ),
    )[:limit]


def build_partner_shortlist(
    organizations: Iterable[ResearchOrganization],
    *,
    target_tissue: str = "",
    limit: int = 12,
) -> list[dict[str, object]]:
    """Rank organizations by fit for collaboration or benchmarking."""

    rows = []
    tissue = target_tissue.lower()
    for organization in organizations:
        text = " ".join(
            [
                organization.name,
                organization.org_type,
                organization.country,
                organization.city,
                organization.focus,
                " ".join(organization.tags),
                organization.notes,
            ]
        ).lower()
        score = 0.25
        reasons = []
        if "partial_reprogramming" in organization.tags or "reprogramming" in text:
            score += 0.28
            reasons.append("部分重编程相关")
        if "ai" in organization.tags or "single_cell" in organization.tags or "comput" in text:
            score += 0.14
            reasons.append("AI/单细胞/计算能力")
        if "delivery" in organization.tags or "gene_therapy" in organization.tags or "mrna" in organization.tags:
            score += 0.12
            reasons.append("递送或基因表达平台")
        if tissue and tissue in text:
            score += 0.10
            reasons.append(f"匹配组织：{target_tissue}")
        if organization.country == "China":
            score += 0.05
            reasons.append("国内合作半径更短")
        if organization.org_type in {"institute", "university", "lab"}:
            score += 0.04
            reasons.append("适合早期课题合作")
        rows.append(
            {
                "name": organization.name,
                "type": organization.org_type,
                "country": organization.country,
                "city": organization.city,
                "fit_score": round(_clamp(score), 6),
                "fit_reason": "；".join(reasons) if reasons else "背景跟踪对象",
                "outreach_angle": _partner_outreach_angle(organization, target_tissue),
                "url": organization.url,
                "caution": "需人工核验代表论文、负责人、真实在研方向和合作意愿",
            }
        )
    return sorted(rows, key=lambda row: (-float(row["fit_score"]), str(row["country"]), str(row["name"])))[:limit]


def build_data_room_checklist(
    *,
    summary: Mapping[str, object],
    audit: Mapping[str, object],
    method_card: Mapping[str, object],
    gene_portfolio: Iterable[Mapping[str, object]],
    evidence_packs: Iterable[Mapping[str, object]],
    stress_rows: Iterable[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Create a data-room checklist that distinguishes present assets from gaps."""

    counts = summary.get("counts", {})
    portfolio = list(gene_portfolio)
    packs = list(evidence_packs)
    stress = list(stress_rows)
    core_count = sum(1 for row in portfolio if row.get("bucket") == "核心候选")
    backed_packs = sum(1 for pack in packs if int(pack.get("paper_count", 0)) >= 3)
    red_flags = list(audit.get("red_flags", []))
    return [
        {
            "item": "数据库清单",
            "status": "已具备" if summary.get("database_ready") else "部分具备",
            "evidence": f"论文 {counts.get('papers', 0)}，候选基因 {counts.get('candidate_genes', 0)}，机构 {counts.get('organizations', 0)}",
            "next_action": "导出 schema、字段字典和数据来源说明",
        },
        {
            "item": "评分方法卡",
            "status": "已具备" if method_card.get("method_version") else "缺失",
            "evidence": str(method_card.get("method_version", "-")),
            "next_action": "冻结版本，并记录每次文献导入后的评分 diff",
        },
        {
            "item": "Top 基因证据包",
            "status": "部分具备" if backed_packs else "待补强",
            "evidence": f"{backed_packs}/{len(packs)} 个证据包已有至少 3 篇本地文献",
            "next_action": "人工复核 PMID、模型、readout、安全风险和失败证据",
        },
        {
            "item": "权重敏感性",
            "status": "已具备" if stress else "缺失",
            "evidence": f"已测试 {len(stress)} 个候选的平衡/安全/年轻化/证据优先场景",
            "next_action": "把高敏感候选移出核心叙事或补证据",
        },
        {
            "item": "核心候选边界",
            "status": "部分具备" if core_count else "待补强",
            "evidence": f"核心候选 {core_count} 个；低证据高分候选被转入补证据候选",
            "next_action": "只用可复核证据支撑核心候选，不把启发式高分当结论",
        },
        {
            "item": "专家复核",
            "status": "缺失",
            "evidence": "；".join(str(flag) for flag in red_flags[-2:]) if red_flags else "尚无专家签名",
            "next_action": "找 2-3 位表观重编程/单细胞/递送专家做盲审备注",
        },
        {
            "item": "外包实验报价",
            "status": "缺失",
            "evidence": "尚未接入 CRO 或高校实验反馈",
            "next_action": "用实验 backlog 生成询价包，拿到报价和可行性反馈",
        },
    ]


def gene_score_report_rows(scores: Iterable[GeneScore]) -> list[dict[str, object]]:
    """Build GUI/report-friendly rows for gene scores."""

    rows = []
    for rank, score in enumerate(scores, start=1):
        rows.append(
            {
                "rank": rank,
                "id": score.gene_id,
                "symbol": score.symbol,
                "matched": score.matched,
                "score": score.total_score,
                "rejuvenation_potential": score.rejuvenation_potential,
                "risk": score.risk_score,
                "safety": score.safety_score,
                "risk_band": _localized_risk_band(score.risk_band),
                "recommendation": score.recommendation,
                "mechanism": score.mechanism,
                "tissues": "、".join(score.target_tissues),
                "evidence_query": score.evidence_query,
                "warnings": list(score.warnings),
                "components": score.components,
                "evidence_basis": score.evidence_basis,
                "literature_count": score.literature_count,
                "evidence_pmids": list(score.evidence_pmids),
                "provenance_score": score.provenance_score,
                "audit_notes": list(score.audit_notes),
            }
        )
    return rows


def organization_report_rows(organizations: Iterable[ResearchOrganization]) -> list[dict[str, object]]:
    """Build GUI/report-friendly rows for organizations."""

    return [
        {
            "id": organization.org_id,
            "name": organization.name,
            "type": organization.org_type,
            "country": organization.country,
            "city": organization.city,
            "focus": organization.focus,
            "tags": "、".join(organization.tags),
            "url": organization.url,
            "notes": organization.notes,
        }
        for organization in sorted(organizations, key=lambda org: (org.org_type, org.country, org.name))
    ]


def asset_summary(
    *,
    paper_count: int,
    genes: Iterable[CandidateGene],
    organizations: Iterable[ResearchOrganization],
) -> dict[str, object]:
    """Summarize progress toward the first database milestone."""

    gene_count = len(list(genes))
    org_count = len(list(organizations))
    targets = {"papers": 100, "candidate_genes": 100, "organizations": 50}
    counts = {"papers": int(paper_count), "candidate_genes": gene_count, "organizations": org_count}
    return {
        "counts": counts,
        "targets": targets,
        "completion": {key: round(min(1.0, counts[key] / targets[key]), 3) for key in targets},
        "database_ready": all(counts[key] >= targets[key] for key in targets),
        "missing": {key: max(0, targets[key] - counts[key]) for key in targets},
    }


def audit_asset_quality(
    *,
    papers: Iterable[object],
    genes: Iterable[CandidateGene],
    organizations: Iterable[ResearchOrganization],
) -> dict[str, object]:
    """Audit whether the database is merely large or actually credible."""

    paper_list = list(papers)
    gene_list = list(genes)
    org_list = list(organizations)
    pmid_count = len({str(getattr(paper, "pmid", "")) for paper in paper_list if str(getattr(paper, "pmid", ""))})
    doi_count = sum(1 for paper in paper_list if str(getattr(paper, "doi", "")).strip())
    high_signal = sum(1 for paper in paper_list if _paper_evidence_score(paper) >= 0.65)
    gene_query_coverage = sum(1 for gene in gene_list if gene.evidence_query.strip())
    literature_backed_genes = sum(1 for gene in gene_list if papers_for_gene(gene, paper_list))
    high_risk_flagged = sum(1 for gene in gene_list if gene.oncogenic_risk >= 0.70 or gene.dedifferentiation_risk >= 0.65)
    url_coverage = sum(1 for org in org_list if org.url.startswith("http"))
    china_orgs = sum(1 for org in org_list if org.country == "China")
    paper_score = min(1.0, pmid_count / 100) * 0.25 + min(1.0, high_signal / 40) * 0.15 + min(1.0, doi_count / max(1, pmid_count)) * 0.08
    gene_score = (
        min(1.0, len(gene_list) / 100) * 0.08
        + min(1.0, gene_query_coverage / max(1, len(gene_list))) * 0.05
        + min(1.0, literature_backed_genes / 50) * 0.22
    )
    org_score = min(1.0, len(org_list) / 50) * 0.04 + min(1.0, url_coverage / max(1, len(org_list))) * 0.04
    expert_review_score = 0.0
    credibility = round(min(0.82, _clamp(paper_score + gene_score + org_score + expert_review_score)), 6)
    red_flags = []
    if pmid_count < 100:
        red_flags.append("论文库未达到 100 篇 PubMed 记录")
    if high_signal < 30:
        red_flags.append("高证据分论文不足，需继续人工筛选核心文献")
    if gene_query_coverage < len(gene_list):
        red_flags.append("部分基因缺少可复核检索式")
    if literature_backed_genes < 50:
        red_flags.append("多数候选基因还没有 PMID 级本地文献命中")
    if url_coverage < len(org_list):
        red_flags.append("部分机构缺少官网 URL")
    red_flags.append("尚未完成外部专家复核，因此可信度分设置上限")
    red_flags.append("候选基因分数仍是启发式研发优先级，不是实验结论")
    next_steps = (
        "为 Top 20 基因补 PMID 级证据包：模型、组织、readout、安全风险、复现实验边界。",
        "对公司/课题组做人工复核：负责人、代表论文、融资/合作状态、是否真的做部分重编程。",
        "把评分权重冻结成版本化方法学，并保留每次文献导入后的评分 diff。",
    )
    return {
        "credibility_score": credibility,
        "credibility_grade": _credibility_grade(credibility),
        "paper": {
            "records": len(paper_list),
            "unique_pmids": pmid_count,
            "doi_count": doi_count,
            "high_signal_count": high_signal,
        },
        "gene": {
            "records": len(gene_list),
            "query_coverage": gene_query_coverage,
            "literature_backed": literature_backed_genes,
            "high_risk_flagged": high_risk_flagged,
        },
        "organization": {
            "records": len(org_list),
            "url_coverage": url_coverage,
            "china_records": china_orgs,
        },
        "red_flags": red_flags,
        "next_steps": list(next_steps),
    }


def investor_diligence_rows(
    *,
    audit: Mapping[str, object],
    gene_scores: Iterable[GeneScore],
) -> list[dict[str, object]]:
    """Generate investor-facing due-diligence talking points."""

    scores = list(gene_scores)
    literature_backed = [score for score in scores if score.evidence_basis == "literature_adjusted"]
    high_provenance = sorted(scores, key=lambda score: (-score.provenance_score, -score.total_score))[:5]
    return [
        {
            "question": "这是不是拍脑袋评分？",
            "answer": (
                "不是单纯拍脑袋：每个基因有固定组件分、风险分和检索式；"
                f"当前 {len(literature_backed)} 个基因已有本地文献命中调整。"
            ),
            "evidence": "Top provenance genes: " + "、".join(score.symbol for score in high_provenance),
        },
        {
            "question": "数据库有没有过线？",
            "answer": (
                f"论文 {audit.get('paper', {}).get('records', 0)} 篇，"
                f"候选基因 {audit.get('gene', {}).get('records', 0)} 个，"
                f"公司/课题组 {audit.get('organization', {}).get('records', 0)} 个；"
                f"可信度等级 {audit.get('credibility_grade')}。"
            ),
            "evidence": "PMID/URL/schema checks are represented in the audit payload.",
        },
        {
            "question": "最大风险是什么？",
            "answer": "最大风险不是 AI 不够强，而是生物学验证窗口窄：癌变、去分化、递送和组织特异性必须逐层验证。",
            "evidence": "Red flags: " + "；".join(str(item) for item in audit.get("red_flags", [])[:3]),
        },
        {
            "question": "下一步花钱买什么确定性？",
            "answer": "先买证据确定性和合作确定性：Top 20 基因证据包、Top 10 机构人工复核、1-2 个可外包体外 readout 设计。",
            "evidence": "Next steps: " + "；".join(str(item) for item in audit.get("next_steps", [])[:2]),
        },
    ]


def find_gene(query: str, genes: Iterable[CandidateGene]) -> CandidateGene | None:
    """Find a gene by symbol or alias."""

    cleaned = query.strip().upper()
    for gene in genes:
        if gene.symbol == cleaned or cleaned in {alias.upper() for alias in gene.aliases}:
            return gene
    return None


def gene_safety_score(gene: CandidateGene) -> float:
    """Convert oncogenic and identity-loss risk into a safety score."""

    return _clamp(1.0 - (gene.oncogenic_risk * 0.58 + gene.dedifferentiation_risk * 0.42))


def papers_for_gene(gene: CandidateGene, papers: Iterable[object]) -> list[object]:
    """Find local papers that mention a gene symbol or alias."""

    tokens = [gene.symbol, *gene.aliases]
    filtered_tokens = [token for token in tokens if len(token.strip()) >= 3]
    matches = []
    for paper in papers:
        text = f"{getattr(paper, 'title', '')}\n{getattr(paper, 'abstract', '')}"
        if any(_contains_token(text, token) for token in filtered_tokens):
            matches.append(paper)
    return sorted(matches, key=lambda paper: (-_paper_evidence_score(paper), -int(getattr(paper, "year", 0) or 0)))


def _gene_recommendation(total: float, safety: float, evidence: float) -> str:
    if total >= 0.68 and safety >= 0.55 and evidence >= 0.55:
        return "优先进入 AI 文献复核和体外验证设计"
    if total >= 0.56 and safety >= 0.45:
        return "观察名单，需要安全闸门和证据补强"
    if safety < 0.35:
        return "高风险基准或风险标志，不建议作为候选"
    return "先补机制和文献证据"


def _contains_token(text: str, token: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])", text, flags=re.IGNORECASE) is not None


def _paper_evidence_score(paper: object) -> float:
    signals = getattr(paper, "signals", None)
    try:
        return float(getattr(signals, "evidence_score", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _paper_signal_tuple(paper: object, field: str) -> tuple[str, ...]:
    signals = getattr(paper, "signals", None)
    value = getattr(signals, field, ())
    if isinstance(value, tuple):
        return tuple(str(item) for item in value)
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return ()


def _paper_contribution(paper: object) -> str:
    parts = []
    readouts = _paper_signal_tuple(paper, "readouts")
    tissues = _paper_signal_tuple(paper, "tissues")
    risks = _paper_signal_tuple(paper, "safety_risks")
    models = _paper_signal_tuple(paper, "models")
    if models:
        parts.append("模型：" + "、".join(models))
    if tissues:
        parts.append("组织：" + "、".join(tissues))
    if readouts:
        parts.append("readout：" + "、".join(readouts))
    if risks:
        parts.append("风险：" + "、".join(risks))
    return "；".join(parts) if parts else "背景证据"


def _evidence_pack_summary(
    gene: CandidateGene,
    paper_count: int,
    average_score: float,
    risks: list[str],
) -> str:
    if paper_count == 0:
        return f"{gene.symbol} 暂无本地 PMID 命中，当前只能作为待检索候选。"
    risk_text = "；风险信号：" + "、".join(risks) if risks else "；暂未抽取到明确安全风险词。"
    return f"{gene.symbol} 命中 {paper_count} 篇本地论文，平均证据分 {average_score:.2f}{risk_text}"


def _stability_label(spread: float) -> str:
    if spread <= 0.045:
        return "稳定"
    if spread <= 0.09:
        return "中等敏感"
    return "高度敏感"


def _stress_decision(average: float, spread: float, min_safety: float) -> str:
    if average >= 0.62 and spread <= 0.07 and min_safety >= 0.55:
        return "稳健候选"
    if min_safety < 0.40:
        return "安全敏感"
    if spread > 0.09:
        return "权重敏感，需复核"
    return "保留观察"


def _portfolio_reason(score: GeneScore) -> str:
    return (
        f"score {score.total_score:.2f}; safety {score.safety_score:.2f}; "
        f"provenance {score.provenance_score:.2f}; papers {score.literature_count}"
    )


def _symbol_list(rows: Iterable[Mapping[str, object]], key: str = "symbol", limit: int = 4) -> str:
    symbols = [str(row.get(key, "")).strip() for row in rows]
    filtered = [symbol for symbol in symbols if symbol]
    return "、".join(filtered[:limit])


def _priority_rank(priority: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(priority, 9)


def _backlog_lane_rank(lane: str) -> int:
    return {
        "证据补强": 0,
        "体外验证设计": 1,
        "安全闸门": 2,
        "组织路线": 3,
        "安全反例": 4,
        "观察池": 5,
    }.get(lane, 9)


def _partner_outreach_angle(organization: ResearchOrganization, target_tissue: str) -> str:
    if organization.org_type == "company":
        if "ai" in organization.tags or "single_cell" in organization.tags:
            return "以数据互补/候选复核切入，避免一上来谈全栈合作"
        if "delivery" in organization.tags or "gene_therapy" in organization.tags or "mrna" in organization.tags:
            return "以递送可控表达和安全开关评估切入"
        return "以竞品/生态情报跟踪为主，先人工确认真实项目边界"
    if target_tissue:
        return f"以 {target_tissue} 组织模型、readout 设计或小规模验证合作切入"
    return "以证据包复核、课题共创或学生项目合作切入"


def _credibility_grade(score: float) -> str:
    if score >= 0.85:
        return "A- 可进入严肃尽调"
    if score >= 0.70:
        return "B+ 可演示，需补专家复核"
    if score >= 0.55:
        return "B 演示可信，证据仍薄"
    return "C 仅原型"


def _risk_band(gene: CandidateGene, safety: float) -> str:
    if safety < 0.35 or gene.oncogenic_risk >= 0.75 or gene.dedifferentiation_risk >= 0.75:
        return "high"
    if safety < 0.55:
        return "medium"
    return "low"


def _localized_risk_band(value: str) -> str:
    return {"high": "高", "medium": "中", "low": "低", "unknown": "未知"}.get(value, value)


def _gene_warnings(gene: CandidateGene, safety: float) -> tuple[str, ...]:
    warnings = []
    if gene.oncogenic_risk >= 0.70:
        warnings.append("癌变/异常增殖风险高")
    if gene.dedifferentiation_risk >= 0.65:
        warnings.append("去分化或细胞身份丢失风险高")
    if safety < 0.55:
        warnings.append("需要短暂表达和强安全闸门")
    if gene.evidence_strength < 0.45:
        warnings.append("证据强度不足")
    return tuple(warnings)


def _default_gene_query(symbol: str, tissues: tuple[str, ...]) -> str:
    tissue_text = " OR ".join(tissues[:3]) if tissues else "aging"
    return f'("{symbol}" aging rejuvenation partial reprogramming) ({tissue_text}) safety'


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
    raw = _required(row, field)
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"Field {field!r} must be a float") from exc
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"Field {field!r} must be between 0.0 and 1.0")
    return value


def _split_required(value: str) -> tuple[str, ...]:
    items = _split_optional(value)
    if not items:
        raise ValueError("Expected at least one semicolon-separated value")
    return items


def _split_optional(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(";") if part.strip())


def _ensure_unique(field: str, values: list[str]) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"Duplicate {field} values are not allowed")


def _validated_weights(weights: Mapping[str, float]) -> dict[str, float]:
    expected = set(GENE_SCORE_WEIGHTS)
    actual = set(weights)
    if actual != expected:
        raise ValueError("Gene score weights must match the expected components")
    normalized = {key: float(value) for key, value in weights.items()}
    if any(value < 0.0 for value in normalized.values()):
        raise ValueError("Gene score weights must be non-negative")
    if sum(normalized.values()) <= 0.0:
        raise ValueError("At least one gene score weight must be positive")
    return normalized


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))
