import unittest

from gerodrug_sim.molecular_workflow import analyze_molecule
from gerodrug_sim.molecule import analyze_smiles
from gerodrug_sim.targets import load_aging_targets, load_known_ligands, predict_targets


class MolecularWorkflowTests(unittest.TestCase):
    def test_analyze_smiles_returns_properties(self):
        props = analyze_smiles("CN(C)C(=N)N=C(N)N")

        self.assertTrue(props.valid)
        self.assertGreater(props.molecular_weight, 100)
        self.assertGreaterEqual(props.oral_likeness, 0)
        self.assertIn(props.herg_risk, {"低", "中", "高", "未知"})

    def test_predict_targets_from_known_ligand_similarity(self):
        predictions = predict_targets("CN(C)C(=N)N=C(N)N")

        self.assertTrue(predictions)
        self.assertEqual(predictions[0].target_id, "AMPK")
        self.assertGreater(predictions[0].probability, 0.5)

    def test_full_molecular_workflow_scores_and_docking(self):
        result = analyze_molecule("CN(C)C(=N)N=C(N)N")

        self.assertIn("properties", result)
        self.assertIn("predictions", result)
        self.assertIn("docking", result)
        self.assertIn("score", result)
        self.assertGreater(result["score"]["total"], 0)

    def test_target_and_ligand_data_load(self):
        self.assertGreaterEqual(len(load_aging_targets()), 8)
        self.assertGreaterEqual(len(load_known_ligands()), 8)


if __name__ == "__main__":
    unittest.main()
