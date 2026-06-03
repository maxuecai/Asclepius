from pathlib import Path
import unittest

from gerodrug_sim.reprogramming import (
    ReprogrammingFactor,
    combination_report_rows,
    design_reprogramming_combinations,
    design_tissue_reprogramming_plans,
    design_validation_experiment,
    evidence_attribution_rows,
    evidence_gap_rows,
    explain_reprogramming_score,
    load_reprogramming_factors,
    rank_reprogramming_factors,
    rank_reprogramming_factors_with_literature,
    reprogramming_report_rows,
    reprogramming_safety_score,
    safety_gate_rows,
    score_reprogramming_factor,
    score_reprogramming_factor_with_literature,
    suggest_reprogramming_next_steps,
    tissue_plan_report_rows,
)


ROOT = Path(__file__).resolve().parents[1]


class _Signals:
    def __init__(self, evidence_score=0.0, safety_risks=(), tissues=(), readouts=()):
        self.evidence_score = evidence_score
        self.safety_risks = safety_risks
        self.tissues = tissues
        self.readouts = readouts


class _Paper:
    def __init__(self, signals, pmid="1", year=2026, title="Example paper"):
        self.signals = signals
        self.pmid = pmid
        self.year = year
        self.title = title


class ReprogrammingTests(unittest.TestCase):
    def test_loads_curated_reprogramming_factors(self):
        factors = load_reprogramming_factors(ROOT / "data" / "reprogramming_factors.csv")

        self.assertGreaterEqual(len(factors), 8)
        self.assertEqual(factors[0].factor_id, "osk")
        self.assertIn("retina", factors[0].target_tissues)
        self.assertGreater(factors[0].rejuvenation_potential, 0.8)

    def test_safety_score_penalizes_oncogenic_and_dedifferentiation_risk(self):
        safe = ReprogrammingFactor(
            factor_id="safe",
            name="Safe",
            modality="gene_axis",
            target_tissues=("fibroblast",),
            rejuvenation_potential=0.6,
            identity_preservation=0.8,
            oncogenic_risk=0.1,
            dedifferentiation_risk=0.1,
            delivery_feasibility=0.6,
            tissue_specificity=0.6,
            evidence_strength=0.5,
            druggability=0.5,
            novelty_ip=0.5,
        )
        risky = ReprogrammingFactor(
            factor_id="risky",
            name="Risky",
            modality="pluripotency_factor",
            target_tissues=("fibroblast",),
            rejuvenation_potential=0.9,
            identity_preservation=0.2,
            oncogenic_risk=0.9,
            dedifferentiation_risk=0.9,
            delivery_feasibility=0.6,
            tissue_specificity=0.6,
            evidence_strength=0.6,
            druggability=0.3,
            novelty_ip=0.3,
        )

        self.assertGreater(reprogramming_safety_score(safe), reprogramming_safety_score(risky))
        self.assertLess(score_reprogramming_factor(risky).safety_score, 0.2)

    def test_ranking_is_deterministic_and_reportable(self):
        factors = load_reprogramming_factors(ROOT / "data" / "reprogramming_factors.csv")
        ranked = rank_reprogramming_factors(factors)
        rows = reprogramming_report_rows(ranked[:3])

        self.assertEqual([score.priority_score for score in ranked], sorted(
            [score.priority_score for score in ranked],
            reverse=True,
        ))
        self.assertEqual(rows[0]["rank"], 1)
        self.assertIn("recommendation", rows[0])
        self.assertIn("components", rows[0])

    def test_literature_adjustment_updates_evidence_and_risk_trace(self):
        factor = ReprogrammingFactor(
            factor_id="osk",
            name="OSK",
            modality="cocktail",
            target_tissues=("retina",),
            rejuvenation_potential=0.7,
            identity_preservation=0.6,
            oncogenic_risk=0.2,
            dedifferentiation_risk=0.2,
            delivery_feasibility=0.5,
            tissue_specificity=0.5,
            evidence_strength=0.2,
            druggability=0.2,
            novelty_ip=0.5,
        )
        papers = [
            _Paper(_Signals(0.8, ("oncogenic risk",), ("retina/optic nerve",), ("function", "RNA-seq"))),
            _Paper(_Signals(0.7, (), ("brain/neuron",), ("function",))),
        ]

        base = score_reprogramming_factor(factor)
        adjusted = score_reprogramming_factor_with_literature(factor, papers)

        self.assertEqual(adjusted.evidence_basis, "literature_adjusted")
        self.assertEqual(adjusted.literature_count, 2)
        self.assertIn("oncogenic risk", adjusted.safety_warnings)
        self.assertGreater(adjusted.components["evidence_strength"], base.components["evidence_strength"])
        self.assertLess(adjusted.safety_score, base.safety_score)

    def test_literature_adjusted_ranking_rows_include_trace_fields(self):
        factors = load_reprogramming_factors(ROOT / "data" / "reprogramming_factors.csv")[:2]
        papers_by_factor = {
            factors[0].factor_id: [_Paper(_Signals(0.75, (), ("retina/optic nerve",), ("function",)))]
        }
        ranked = rank_reprogramming_factors_with_literature(factors, papers_by_factor)
        rows = reprogramming_report_rows(ranked)

        self.assertIn("evidence_basis", rows[0])
        self.assertIn("literature_count", rows[0])
        self.assertIn("safety_warnings", rows[0])
        self.assertIn("process_notes", rows[0])
        self.assertIn("next_steps", rows[0])

    def test_explanation_and_next_steps_are_human_readable(self):
        factor = load_reprogramming_factors(ROOT / "data" / "reprogramming_factors.csv")[0]
        score = score_reprogramming_factor(factor)

        notes = explain_reprogramming_score(score)
        steps = suggest_reprogramming_next_steps(score)

        self.assertTrue(any("总优先级" in note for note in notes))
        self.assertTrue(any("readout" in step or "文献雷达" in step for step in steps))

    def test_evidence_attribution_and_experiment_design_are_actionable(self):
        paper = _Paper(
            _Signals(0.8, ("oncogenic risk",), ("retina/optic nerve",), ("function", "RNA-seq")),
            pmid="123",
            title="OSK restores retinal function with safety monitoring",
        )
        factor = load_reprogramming_factors(ROOT / "data" / "reprogramming_factors.csv")[0]
        score = score_reprogramming_factor_with_literature(factor, [paper])

        attribution = evidence_attribution_rows([paper])
        design = design_validation_experiment(score)

        self.assertIn("安全扣分", attribution[0]["contribution"])
        self.assertIn("readout", attribution[0]["contribution"])
        self.assertIn("objective", design)
        self.assertIn("decision_gate", design)
        self.assertGreaterEqual(len(design["safety_readouts"]), 3)

    def test_combination_design_separates_candidates_from_benchmarks(self):
        factors = load_reprogramming_factors(ROOT / "data" / "reprogramming_factors.csv")
        ranked = rank_reprogramming_factors(factors)

        combinations = design_reprogramming_combinations(ranked, target_tissue="fibroblast")
        rows = combination_report_rows(combinations)

        self.assertGreaterEqual(len(rows), 2)
        self.assertEqual(rows[0]["rank"], 1)
        self.assertIn("strategy", rows[0])
        self.assertIn("validation_plan", rows[0])
        self.assertTrue(any(row["id"] == "gated_osk_core" for row in rows))
        benchmark = next(row for row in rows if row["id"] == "high_risk_benchmark")
        self.assertEqual(benchmark["risk_profile"], "仅基准")
        self.assertIn("MYC", benchmark["factors"])

    def test_tissue_plans_safety_gates_and_evidence_gaps_support_ai_loop(self):
        factors = load_reprogramming_factors(ROOT / "data" / "reprogramming_factors.csv")
        ranked = rank_reprogramming_factors(factors)
        combinations = design_reprogramming_combinations(ranked, target_tissue="retina")

        tissue_rows = tissue_plan_report_rows(
            design_tissue_reprogramming_plans(ranked, combinations, focus_tissues=("retina", "immune"))
        )
        gate_rows = safety_gate_rows([ranked[0], *combinations])
        gap_rows = evidence_gap_rows(ranked)

        self.assertGreaterEqual(len(tissue_rows), 2)
        self.assertIn("model_system", tissue_rows[0])
        self.assertIn("delivery_focus", tissue_rows[0])
        self.assertTrue(any(row["gate"] in {"红灯", "黄灯", "绿灯"} for row in gate_rows))
        self.assertIn("stop_triggers", gate_rows[0])
        self.assertIn("query", gap_rows[0])
        self.assertIn("AI", gap_rows[0]["ai_task"])


if __name__ == "__main__":
    unittest.main()
