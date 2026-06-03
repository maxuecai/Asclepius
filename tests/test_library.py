import csv
import tempfile
from pathlib import Path
import unittest

from gerodrug_sim.library import (
    MoleculeLibrary,
    import_seed_library,
    initialize_schema,
    list_compounds,
    open_library,
    search_compounds,
)


class MoleculeLibraryTests(unittest.TestCase):
    def test_open_initializes_schema_and_upserts_compounds(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "library.sqlite"

            with open_library(db_path) as library:
                created = library.upsert_compound("Metformin", "CN(C)C(=N)N=C(N)N", "original")
                updated = library.upsert_compound("Metformin XR", "CN(C)C(=N)N=C(N)N", "updated")

                self.assertEqual(created.compound_id, updated.compound_id)
                self.assertEqual(updated.name, "Metformin XR")
                self.assertEqual(updated.notes, "updated")

            self.assertTrue(db_path.exists())

    def test_import_csv_lists_and_searches_compounds(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "molecules.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=("name", "smiles", "notes"))
                writer.writeheader()
                writer.writerow({"name": "Metformin", "smiles": "CN(C)C(=N)N=C(N)N", "notes": "AMPK"})
                writer.writerow({"name": "Resveratrol", "smiles": "Oc1ccc(/C=C/c2cc(O)cc(O)c2)cc1", "notes": "SIRT1"})

            with MoleculeLibrary(Path(tmpdir) / "library.sqlite") as library:
                imported = library.import_csv(csv_path)
                all_compounds = library.list_compounds()
                matches = library.search_compounds("sirt")

                self.assertEqual(imported, 2)
                self.assertEqual([compound.name for compound in all_compounds], ["Metformin", "Resveratrol"])
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0].name, "Resveratrol")

    def test_store_analysis_json_and_external_ids(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with MoleculeLibrary(Path(tmpdir) / "library.sqlite") as library:
                compound = library.upsert_compound("Metformin", "CN(C)C(=N)N=C(N)N")
                analysis = library.store_analysis(
                    compound.compound_id,
                    {"score": {"total": 0.82}, "targets": ["AMPK"]},
                    analysis_type="ranking",
                )
                library.add_external_id(compound.compound_id, "PubChem", "4091")

                analyses = library.list_analyses(compound.compound_id, analysis_type="ranking")
                external_ids = library.list_external_ids(compound.compound_id)

                self.assertEqual(analysis.payload["score"]["total"], 0.82)
                self.assertEqual(analyses[0].payload["targets"], ["AMPK"])
                self.assertEqual(external_ids, {"PubChem": "4091"})

    def test_seed_importer_uses_sample_molecules(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with MoleculeLibrary(Path(tmpdir) / "library.sqlite") as library:
                imported = import_seed_library(library.connection)
                matches = library.search_compounds("二甲双胍")

                self.assertGreaterEqual(imported, 4)
                self.assertEqual(matches[0].smiles, "CN(C)C(=N)N=C(N)N")

    def test_module_level_functions_accept_existing_connection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            library = MoleculeLibrary(Path(tmpdir) / "library.sqlite")
            try:
                initialize_schema(library.connection)
                library.upsert_compound("Quercetin", "O=c1c(O)c(-c2ccc(O)c(O)c2)oc2cc(O)cc(O)c12")

                self.assertEqual(len(list_compounds(library.connection)), 1)
                self.assertEqual(search_compounds(library.connection, query="quer")[0].name, "Quercetin")
            finally:
                library.close()


if __name__ == "__main__":
    unittest.main()
