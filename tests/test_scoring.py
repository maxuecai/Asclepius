from pathlib import Path
import unittest

from gerodrug_sim.data import (
    AgingHallmark,
    CandidateDrug,
    load_candidates,
    load_evidence_sources,
    load_hallmarks,
    load_software_tools,
    load_trial_endpoints,
)
from gerodrug_sim.scoring import (
    hallmark_target_score,
    rank_candidates,
    score_candidate,
)


ROOT = Path(__file__).resolve().parents[1]


class ScoringTests(unittest.TestCase):
    def test_loads_sample_data_with_clear_schema(self):
        hallmarks = load_hallmarks(ROOT / "data" / "aging_hallmarks.csv")
        candidates = load_candidates(ROOT / "data" / "candidate_drugs.csv")

        self.assertEqual(hallmarks[0].hallmark_id, "genomic_instability")
        self.assertEqual(len(hallmarks), 12)
        self.assertEqual(candidates[0].candidate_id, "rapamycin")
        self.assertEqual(candidates[0].target_hallmarks, ("nutrient_sensing", "proteostasis", "macroautophagy", "inflammation"))
        self.assertIn("hallmarks2023", candidates[0].evidence_sources)

    def test_scores_candidate_from_weighted_components(self):
        hallmarks = [
            AgingHallmark("a", "Hallmark A", 0.25),
            AgingHallmark("b", "Hallmark B", 0.75),
        ]
        candidate = CandidateDrug(
            candidate_id="drug_a",
            name="Drug A",
            target_hallmarks=("b",),
            expression_reversal=0.80,
            safety=0.70,
            translational_evidence=0.60,
            trial_feasibility=0.50,
        )

        score = score_candidate(candidate, hallmarks)

        self.assertEqual(score.components["hallmark_target"], 0.75)
        self.assertEqual(score.components["regulatory_readiness"], 0.5)
        self.assertEqual(score.components["biomarker_relevance"], 0.5)
        self.assertEqual(score.total_score, 0.661)

    def test_ranking_is_descending_and_deterministic(self):
        hallmarks = load_hallmarks(ROOT / "data" / "aging_hallmarks.csv")
        candidates = load_candidates(ROOT / "data" / "candidate_drugs.csv")

        ranked = rank_candidates(candidates, hallmarks)

        self.assertEqual(ranked[0].candidate_id, "metformin")
        self.assertEqual([score.total_score for score in ranked], sorted(
            [score.total_score for score in ranked],
            reverse=True,
        ))

    def test_loads_research_sources_and_trial_endpoints(self):
        sources = load_evidence_sources(ROOT / "data" / "evidence_sources.csv")
        endpoints = load_trial_endpoints(ROOT / "data" / "trial_endpoints.csv")
        tools = load_software_tools(ROOT / "data" / "software_tools.csv")

        self.assertGreaterEqual(len(sources), 5)
        self.assertGreaterEqual(len(endpoints), 5)
        self.assertGreaterEqual(len(tools), 5)
        self.assertEqual(sources[0].source_id, "hallmarks2023")
        self.assertEqual(endpoints[0].endpoint_id, "multimorbidity")
        self.assertEqual(tools[0].tool_id, "rdkit")

    def test_unknown_hallmark_is_rejected(self):
        candidate = CandidateDrug(
            candidate_id="bad",
            name="Bad",
            target_hallmarks=("unknown",),
            expression_reversal=0.5,
            safety=0.5,
            translational_evidence=0.5,
            trial_feasibility=0.5,
        )

        with self.assertRaisesRegex(ValueError, "unknown hallmarks"):
            hallmark_target_score(candidate, [AgingHallmark("known", "Known", 1.0)])


if __name__ == "__main__":
    unittest.main()
