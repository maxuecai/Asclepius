import json
import unittest

from gerodrug_sim.external import (
    build_bindingdb_ligand_url,
    build_chembl_similarity_url,
    build_pubchem_name_property_url,
    build_rcsb_entry_url,
    fetch_json,
    parse_chembl_results,
    parse_pubchem_compounds,
    summarize_external_status,
)


class _MockResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class ExternalClientTests(unittest.TestCase):
    def test_builds_pubchem_name_property_url(self):
        url = build_pubchem_name_property_url("metformin hydrochloride")

        self.assertEqual(
            url,
            "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
            "metformin%20hydrochloride/property/CanonicalSMILES,IsomericSMILES,InChIKey/JSON",
        )

    def test_parses_pubchem_property_json(self):
        compounds = parse_pubchem_compounds(
            {
                "PropertyTable": {
                    "Properties": [
                        {
                            "CID": 4091,
                            "CanonicalSMILES": "CN(C)C(=N)N=C(N)N",
                            "IsomericSMILES": "CN(C)C(=N)N=C(N)N",
                            "InChIKey": "XZWYZXLIPXDOLR-UHFFFAOYSA-N",
                        }
                    ]
                }
            }
        )

        self.assertEqual(compounds[0].cid, 4091)
        self.assertEqual(compounds[0].canonical_smiles, "CN(C)C(=N)N=C(N)N")
        self.assertEqual(compounds[0].inchikey, "XZWYZXLIPXDOLR-UHFFFAOYSA-N")

    def test_builds_chembl_similarity_url(self):
        url = build_chembl_similarity_url("CN(C)C(=N)N=C(N)N", similarity_cutoff=85)

        self.assertEqual(
            url,
            "https://www.ebi.ac.uk/chembl/api/data/similarity/"
            "CN%28C%29C%28%3DN%29N%3DC%28N%29N/85.json",
        )

    def test_parses_chembl_similarity_and_activity_results(self):
        similarity = parse_chembl_results(
            {"molecules": [{"molecule_chembl_id": "CHEMBL1431", "pref_name": "METFORMIN", "similarity": "100"}]}
        )
        activities = parse_chembl_results(
            {
                "activities": [
                    {
                        "molecule_chembl_id": "CHEMBL1431",
                        "target_chembl_id": "CHEMBL2094115",
                        "target_pref_name": "AMPK complex",
                        "standard_type": "IC50",
                        "standard_value": "1200",
                        "standard_units": "nM",
                        "pchembl_value": "5.92",
                    }
                ]
            }
        )

        self.assertEqual(similarity[0].molecule_name, "METFORMIN")
        self.assertEqual(similarity[0].similarity, "100")
        self.assertEqual(activities[0].target_name, "AMPK complex")
        self.assertEqual(activities[0].activity_type, "IC50")
        self.assertEqual(activities[0].activity_units, "nM")

    def test_builds_bindingdb_and_rcsb_urls(self):
        self.assertEqual(
            build_bindingdb_ligand_url(50000001),
            "https://www.bindingdb.org/rwd/bind/chemsearch/marvin/MolStructure.jsp?monomerid=50000001",
        )
        self.assertEqual(
            build_rcsb_entry_url("1a2b"),
            "https://data.rcsb.org/rest/v1/core/entry/1A2B",
        )

    def test_fetch_json_uses_timeout_and_mocked_urlopen(self):
        calls = []

        def opener(request, timeout):
            calls.append((request, timeout))
            return _MockResponse({"ok": True})

        payload = fetch_json("https://example.test/data.json", timeout=2.5, opener=opener)

        self.assertEqual(payload, {"ok": True})
        self.assertEqual(calls[0][1], 2.5)
        self.assertEqual(calls[0][0].get_header("Accept"), "application/json")

    def test_summary_names_configured_sources(self):
        summary = summarize_external_status()

        self.assertIn("PubChem", summary)
        self.assertIn("ChEMBL", summary)
        self.assertIn("BindingDB", summary)
        self.assertIn("RCSB PDB", summary)
        self.assertIn("timeouts", summary)


if __name__ == "__main__":
    unittest.main()
