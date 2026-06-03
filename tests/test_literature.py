import unittest

from gerodrug_sim.literature import (
    Paper,
    ResearchLibrary,
    analyze_paper_signals,
    build_pubmed_fetch_url,
    build_pubmed_search_url,
    parse_pubmed_search_ids,
    parse_pubmed_xml,
    papers_for_factor,
)


SAMPLE_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345</PMID>
      <Article>
        <Journal>
          <Title>Nature Aging</Title>
          <JournalIssue><PubDate><Year>2025</Year></PubDate></JournalIssue>
        </Journal>
        <ArticleTitle>Targeted partial reprogramming with OSK in aged retina</ArticleTitle>
        <Abstract>
          <AbstractText>In mice, AAV-delivered OSK restored retinal function without teratoma formation. RNA-seq and DNA methylation age were measured.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author><ForeName>Ada</ForeName><LastName>Lovelace</LastName></Author>
        </AuthorList>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="doi">10.1234/example</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""


class LiteratureTests(unittest.TestCase):
    def test_builds_pubmed_urls_and_parses_ids(self):
        self.assertIn("db=pubmed", build_pubmed_search_url("partial reprogramming", retmax=5))
        self.assertIn("retmax=5", build_pubmed_search_url("partial reprogramming", retmax=5))
        self.assertIn("id=123%2C456", build_pubmed_fetch_url(["123", "456"]))
        self.assertEqual(parse_pubmed_search_ids({"esearchresult": {"idlist": ["1", "2"]}}), ["1", "2"])

    def test_parses_pubmed_xml_and_extracts_signals(self):
        papers = parse_pubmed_xml(SAMPLE_XML)

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].pmid, "12345")
        self.assertEqual(papers[0].doi, "10.1234/example")
        self.assertEqual(papers[0].authors, ("Ada Lovelace",))

        signals = analyze_paper_signals(papers[0])
        self.assertIn("partial reprogramming", signals.categories)
        self.assertIn("OSK", signals.interventions)
        self.assertIn("osk", signals.matched_factors)
        self.assertIn("retina/optic nerve", signals.tissues)
        self.assertIn("mouse", signals.models)
        self.assertIn("oncogenic risk", signals.safety_risks)
        self.assertEqual(signals.evidence_level, "animal")
        self.assertGreater(signals.evidence_score, 0.4)

    def test_research_library_upserts_and_searches_papers(self):
        paper = Paper(
            pmid="999",
            title="Partial reprogramming of aged fibroblasts",
            abstract="Human fibroblast RNA-seq shows partial reprogramming without cancer signals.",
            journal="Example Journal",
            year=2026,
            doi="10.0000/test",
            url="https://pubmed.ncbi.nlm.nih.gov/999/",
        )
        with ResearchLibrary(":memory:") as library:
            stored = library.upsert_paper(paper)
            results = library.search_papers("fibroblast")

            self.assertEqual(stored.pmid, "999")
            self.assertEqual(len(results), 1)
            self.assertIn("skin/fibroblast", results[0].signals.tissues)
            self.assertIn("partial reprogramming", results[0].signals.categories)
            self.assertEqual(len(library.search_papers("partial reprogramming aging")), 1)
            self.assertGreater(results[0].signals.evidence_score, 0.0)
            self.assertEqual(papers_for_factor(library.connection, factor_id="osk"), [])


if __name__ == "__main__":
    unittest.main()
