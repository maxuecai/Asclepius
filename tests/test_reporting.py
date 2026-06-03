import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from gerodrug_sim.reporting import (
    main,
    render_markdown_report,
    render_report_from_payload,
)


class ReportingTests(unittest.TestCase):
    def test_render_markdown_report_includes_ranked_candidates_and_trials(self):
        report = render_markdown_report(
            [
                {
                    "name": "Senolytic-A",
                    "mechanism": "BCL-2 inhibition",
                    "score": 0.9123,
                    "safety_score": 0.71,
                    "evidence_level": "preclinical",
                    "recommendation": "advance",
                }
            ],
            [
                {
                    "name": "Frailty prevention",
                    "phase": "IIa",
                    "population": "older adults with high inflammatory markers",
                    "duration": "24 weeks",
                    "primary_endpoint": "frailty index",
                    "outcome": "signal detected",
                }
            ],
            generated_on="2026-05-15",
        )

        self.assertIn("# Asclepius 抗衰药物研发模拟报告", report)
        self.assertIn("Generated: 2026-05-15", report)
        self.assertIn("| 1 | Senolytic-A | BCL-2 inhibition | 0.912 | 0.71 | preclinical | advance |", report)
        self.assertIn("| Frailty prevention | IIa | older adults with high inflammatory markers | 24 weeks | frailty index | signal detected |", report)
        self.assertIn("Scores are simulation outputs, not clinical evidence.", report)

    def test_render_markdown_report_escapes_table_pipes_and_newlines(self):
        report = render_markdown_report(
            [{"name": "Drug | Combo", "mechanism": "mTOR\nAMPK", "score": 1}],
            [{"id": "T|01", "summary": "improved | uncertain"}],
            generated_on="2026-05-15",
        )

        self.assertIn("Drug \\| Combo", report)
        self.assertIn("mTOR AMPK", report)
        self.assertIn("T\\|01", report)
        self.assertIn("improved \\| uncertain", report)

    def test_render_markdown_report_handles_empty_inputs(self):
        report = render_markdown_report([], [], generated_on="2026-05-15")

        self.assertIn("No ranked candidates were provided.", report)
        self.assertIn("No trial summaries were provided.", report)
        self.assertIn("did not produce candidate rankings or trial summaries", report)

    def test_render_report_from_payload_validates_lists(self):
        with self.assertRaises(ValueError):
            render_report_from_payload({"ranked_candidates": {"name": "not a list"}})

    def test_render_markdown_report_can_render_chinese_labels(self):
        report = render_markdown_report(
            [{"name": "二甲双胍", "score": 0.8}],
            [{"name": "衰弱预防", "summary": "信号阳性"}],
            title="抗衰药物研发模拟报告",
            generated_on="2026-05-15",
            language="zh",
        )

        self.assertIn("生成日期: 2026-05-15", report)
        self.assertIn("## 候选药排名", report)
        self.assertIn("| 排名 | 候选药 | 机制 | 评分 | 安全性 | 证据 | 建议 |", report)
        self.assertIn("评分是模拟输出", report)

    def test_cli_writes_report_to_stdout(self):
        payload = {
            "generated_on": "2026-05-15",
            "ranked_candidates": [{"name": "Rapalog-X", "score": 0.8}],
            "trial_summaries": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "payload.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main([str(input_path)])

        self.assertEqual(exit_code, 0)
        self.assertIn("Rapalog-X", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
