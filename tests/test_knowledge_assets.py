from pathlib import Path
import unittest

from gerodrug_sim.knowledge_assets import (
    audit_asset_quality,
    asset_summary,
    build_data_room_checklist,
    build_experiment_backlog,
    build_gene_evidence_pack,
    build_gene_portfolio,
    build_partner_shortlist,
    build_program_milestones,
    gene_score_report_rows,
    investor_diligence_rows,
    load_candidate_genes,
    load_research_organizations,
    rank_candidate_genes,
    rank_candidate_genes_with_literature,
    scoring_method_card,
    score_gene_query,
    score_gene_query_with_literature,
    stress_test_gene_candidate,
    stress_test_report_rows,
)


ROOT = Path(__file__).resolve().parents[1]


class _Signals:
    def __init__(self, evidence_score=0.0, safety_risks=(), tissues=(), readouts=()):
        self.evidence_score = evidence_score
        self.safety_risks = safety_risks
        self.tissues = tissues
        self.readouts = readouts


class _Paper:
    def __init__(self, title, abstract="", pmid="1", doi="10.1/example", year=2026, signals=None):
        self.title = title
        self.abstract = abstract
        self.pmid = pmid
        self.doi = doi
        self.year = year
        self.signals = signals or _Signals()


class KnowledgeAssetTests(unittest.TestCase):
    def test_loads_database_milestone_assets(self):
        genes = load_candidate_genes(ROOT / "data" / "candidate_genes.csv")
        organizations = load_research_organizations(ROOT / "data" / "research_organizations.csv")
        summary = asset_summary(paper_count=100, genes=genes, organizations=organizations)

        self.assertEqual(len(genes), 100)
        self.assertEqual(len(organizations), 50)
        self.assertTrue(summary["database_ready"])
        self.assertEqual(summary["missing"]["candidate_genes"], 0)
        self.assertEqual(summary["missing"]["organizations"], 0)

    def test_scores_known_and_unknown_gene_queries(self):
        genes = load_candidate_genes(ROOT / "data" / "candidate_genes.csv")

        known = score_gene_query("SIRT6", genes)
        unknown = score_gene_query("NEWGENE", genes)

        self.assertTrue(known.matched)
        self.assertEqual(known.symbol, "SIRT6")
        self.assertGreater(known.rejuvenation_potential, 0.5)
        self.assertLess(known.risk_score, 0.4)
        self.assertFalse(unknown.matched)
        self.assertIn("未命中", "；".join(unknown.warnings))

    def test_gene_ranking_rows_are_reportable(self):
        genes = load_candidate_genes(ROOT / "data" / "candidate_genes.csv")
        rows = gene_score_report_rows(rank_candidate_genes(genes)[:5])

        self.assertEqual(rows[0]["rank"], 1)
        self.assertIn("score", rows[0])
        self.assertIn("risk", rows[0])
        self.assertIn("evidence_query", rows[0])

    def test_literature_adjusts_gene_scores_and_provenance(self):
        genes = load_candidate_genes(ROOT / "data" / "candidate_genes.csv")
        papers = [
            _Paper(
                "SIRT6 improves aging chromatin states",
                "SIRT6 function and DNA repair improve fibroblast aging readouts.",
                pmid="123",
                signals=_Signals(0.82, (), ("skin/fibroblast",), ("function", "DNA methylation age")),
            )
        ]

        score = score_gene_query_with_literature("SIRT6", genes, papers)
        rows = gene_score_report_rows([score])

        self.assertEqual(score.evidence_basis, "literature_adjusted")
        self.assertEqual(score.literature_count, 1)
        self.assertIn("123", score.evidence_pmids)
        self.assertGreater(score.provenance_score, 0.5)
        self.assertIn("provenance_score", rows[0])

    def test_asset_audit_and_diligence_rows_are_investor_facing(self):
        genes = load_candidate_genes(ROOT / "data" / "candidate_genes.csv")
        organizations = load_research_organizations(ROOT / "data" / "research_organizations.csv")
        papers = [
            _Paper("SIRT6 aging", pmid=str(index), signals=_Signals(0.7, (), ("fibroblast",), ("function",)))
            for index in range(1, 36)
        ]
        audit = audit_asset_quality(papers=papers, genes=genes, organizations=organizations)
        ranked = rank_candidate_genes_with_literature(genes, papers)
        rows = investor_diligence_rows(audit=audit, gene_scores=ranked)

        self.assertIn("credibility_score", audit)
        self.assertIn("red_flags", audit)
        self.assertGreaterEqual(len(rows), 3)
        self.assertIn("question", rows[0])
        self.assertIn("answer", rows[0])

    def test_evidence_pack_stress_test_and_portfolio_are_actionable(self):
        genes = load_candidate_genes(ROOT / "data" / "candidate_genes.csv")
        sirt6 = next(gene for gene in genes if gene.symbol == "SIRT6")
        papers = [
            _Paper(
                "SIRT6 aging chromatin function",
                "SIRT6 improves function and DNA methylation age in fibroblast aging.",
                pmid="321",
                signals=_Signals(0.82, (), ("skin/fibroblast",), ("function", "DNA methylation age")),
            )
        ]
        ranked = rank_candidate_genes_with_literature(genes, papers)

        pack = build_gene_evidence_pack(sirt6, papers)
        stress = stress_test_gene_candidate(sirt6, papers)
        stress_rows = stress_test_report_rows(genes[:5], papers)
        portfolio = build_gene_portfolio(ranked)
        method = scoring_method_card()

        self.assertEqual(pack["symbol"], "SIRT6")
        self.assertEqual(pack["paper_count"], 1)
        self.assertIn("top_papers", pack)
        self.assertIn("scenario_scores", stress)
        self.assertIn("stability", stress)
        self.assertGreaterEqual(len(stress_rows), 1)
        self.assertTrue(any(row["bucket"] in {"核心候选", "安全辅助轴", "补证据候选", "风险基准", "观察池"} for row in portfolio))
        self.assertIn("method_version", method)

    def test_program_workbench_assets_support_execution_plan(self):
        genes = load_candidate_genes(ROOT / "data" / "candidate_genes.csv")
        organizations = load_research_organizations(ROOT / "data" / "research_organizations.csv")
        papers = [
            _Paper(
                "SOX2 KLF4 partial reprogramming retinal aging",
                "SOX2 and KLF4 improve function with DNA methylation age readouts in retina.",
                pmid="901",
                signals=_Signals(0.78, (), ("retina",), ("function", "DNA methylation age")),
            )
        ]
        ranked = rank_candidate_genes_with_literature(genes, papers)
        portfolio = build_gene_portfolio(ranked)
        packs = [build_gene_evidence_pack(gene, papers) for gene in genes[:5]]
        audit = audit_asset_quality(papers=papers, genes=genes, organizations=organizations)
        summary = asset_summary(paper_count=len(papers), genes=genes, organizations=organizations)
        method = scoring_method_card()
        stress = stress_test_report_rows(genes[:5], papers)
        tissue_plans = [{"label": "retina", "model_system": "retinal cell model"}]
        gates = [{"gate": "黄灯", "name": "OSK", "must_pass": ["identity retention"]}]

        milestones = build_program_milestones(
            gene_portfolio=portfolio,
            evidence_packs=packs,
            audit=audit,
            tissue_plans=tissue_plans,
            safety_gates=gates,
        )
        backlog = build_experiment_backlog(
            gene_portfolio=portfolio,
            evidence_packs=packs,
            tissue_plans=tissue_plans,
            safety_gates=gates,
        )
        partners = build_partner_shortlist(organizations, target_tissue="retina")
        checklist = build_data_room_checklist(
            summary=summary,
            audit=audit,
            method_card=method,
            gene_portfolio=portfolio,
            evidence_packs=packs,
            stress_rows=stress,
        )

        self.assertGreaterEqual(len(milestones), 4)
        self.assertIn("exit_gate", milestones[0])
        self.assertGreaterEqual(len(backlog), 5)
        self.assertIn("success_criteria", backlog[0])
        self.assertGreaterEqual(len(partners), 5)
        self.assertIn("outreach_angle", partners[0])
        self.assertGreaterEqual(len(checklist), 5)
        self.assertIn("next_action", checklist[0])


if __name__ == "__main__":
    unittest.main()
