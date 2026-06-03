import unittest
from dataclasses import asdict

from gerodrug_sim.admet import (
    CYP_ISOFORMS,
    admet_risk_summary,
    discovery_readiness_subscores,
    score_discovery_readiness,
    summarize_admet_risk,
)
from gerodrug_sim.molecule import analyze_smiles
from gerodrug_sim.targets import predict_targets


class ADMETTests(unittest.TestCase):
    def test_summary_includes_required_admet_endpoints(self):
        props = analyze_smiles("CN(C)C(=N)N=C(N)N")
        summary = summarize_admet_risk(props)

        self.assertIn(summary.gi_absorption.level, {"低", "中", "高"})
        self.assertIn(summary.pgp_substrate_likelihood.level, {"低", "中", "高"})
        self.assertEqual(set(summary.cyp_isoform_risks), set(CYP_ISOFORMS))
        self.assertIn(summary.dili_risk.level, {"低", "中", "高"})
        self.assertIn(summary.ames_risk.level, {"低", "中", "高"})
        self.assertIn(summary.mitochondrial_toxicity_risk.level, {"低", "中", "高"})
        self.assertIn(summary.uncertainty.level, {"低", "中", "高"})
        self.assertGreaterEqual(summary.overall_safety_score, 0.0)
        self.assertLessEqual(summary.overall_safety_score, 1.0)

    def test_summary_is_serializable_with_dataclasses_asdict(self):
        props = analyze_smiles("CC(=O)Oc1ccccc1C(=O)O")
        payload = asdict(admet_risk_summary(props))

        self.assertIn("gi_absorption", payload)
        self.assertIn("3A4", payload["cyp_isoform_risks"])
        self.assertIn("overall_safety_score", payload)

    def test_invalid_structure_returns_unknown_high_uncertainty(self):
        props = analyze_smiles("@@@")
        summary = summarize_admet_risk(props)

        self.assertFalse(props.valid)
        self.assertEqual(summary.gi_absorption.level, "未知")
        self.assertEqual(summary.uncertainty.level, "高")
        self.assertEqual(summary.overall_safety_score, 0.0)

    def test_readiness_subscores_use_properties_and_predictions(self):
        props = analyze_smiles("CN(C)C(=N)N=C(N)N")
        predictions = predict_targets(props.smiles)
        scores = discovery_readiness_subscores(props, predictions)

        self.assertEqual(set(scores), {"discovery", "safety", "translatability", "evidence"})
        for value in scores.values():
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)
        self.assertGreater(scores["discovery"], 0.0)
        self.assertEqual(scores, score_discovery_readiness(props, predictions))


if __name__ == "__main__":
    unittest.main()
