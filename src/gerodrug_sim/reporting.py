"""Markdown reporting for the geroprotective drug R&D simulation.

The module intentionally accepts plain Python mappings so it can sit at the
edge of the prototype without forcing a shared domain model on the rest of the
simulation.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any


DEFAULT_TITLE = "Asclepius 抗衰药物研发模拟报告"


def render_markdown_report(
    ranked_candidates: Iterable[Mapping[str, Any]],
    trial_summaries: Iterable[Mapping[str, Any]],
    *,
    title: str = DEFAULT_TITLE,
    generated_on: str | None = None,
    language: str = "en",
) -> str:
    """Render ranked candidates and trial summaries as a Markdown report.

    Required candidate fields are deliberately small: ``name`` plus any scoring
    fields the caller can provide. Trial rows likewise only require an
    identifier or name. Missing optional values render as ``n/a``.
    """

    candidates = list(ranked_candidates)
    trials = list(trial_summaries)
    generated = generated_on or date.today().isoformat()
    text = _labels(language)

    lines = [
        f"# {_clean_text(title)}",
        "",
        f"{text['generated']}: {generated}",
        "",
        f"## {text['summary_heading']}",
        "",
        _summary_sentence(candidates, trials, text),
        "",
        f"## {text['candidates_heading']}",
        "",
    ]

    if candidates:
        lines.extend(
            [
                f"| {text['rank']} | {text['candidate']} | {text['mechanism']} | {text['score']} | {text['safety']} | {text['evidence']} | {text['recommendation']} |",
                "| ---: | --- | --- | ---: | ---: | --- | --- |",
            ]
        )
        for index, candidate in enumerate(candidates, start=1):
            lines.append(_candidate_row(index, candidate))
    else:
        lines.append(text["no_candidates"])

    lines.extend(["", f"## {text['trials_heading']}", ""])

    if trials:
        lines.extend(
            [
                f"| {text['trial']} | {text['phase']} | {text['population']} | {text['duration']} | {text['endpoint']} | {text['outcome']} |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for trial in trials:
            lines.append(_trial_row(trial))
    else:
        lines.append(text["no_trials"])

    lines.extend(
        [
            "",
            f"## {text['limits_heading']}",
            "",
            f"- {text['limit_scores']}",
            f"- {text['limit_rankings']}",
            f"- {text['limit_trials']}",
            "",
        ]
    )
    return "\n".join(lines)


def render_report_from_payload(payload: Mapping[str, Any]) -> str:
    """Render a report from a JSON-compatible payload.

    Expected schema::

        {
          "title": "optional report title",
          "generated_on": "YYYY-MM-DD",
          "ranked_candidates": [{...}],
          "trial_summaries": [{...}]
        }
    """

    return render_markdown_report(
        _as_list(payload.get("ranked_candidates", []), "ranked_candidates"),
        _as_list(payload.get("trial_summaries", []), "trial_summaries"),
        title=str(payload.get("title") or DEFAULT_TITLE),
        generated_on=_optional_string(payload.get("generated_on")),
        language=str(payload.get("language") or "en"),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for rendering a Markdown report from JSON input."""

    parser = argparse.ArgumentParser(
        description="Render an anti-aging drug R&D simulation Markdown report."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="JSON file containing ranked_candidates and trial_summaries.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Markdown output path. Defaults to standard output.",
    )
    args = parser.parse_args(argv)

    try:
        with args.input.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, Mapping):
            raise ValueError("top-level JSON value must be an object")
        report = render_report_from_payload(payload)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"reporting error: {exc}", file=sys.stderr)
        return 2

    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report)
    return 0


def _summary_sentence(
    candidates: list[Mapping[str, Any]], trials: list[Mapping[str, Any]], text: Mapping[str, str]
) -> str:
    if not candidates and not trials:
        return text["empty_summary"]
    top_candidate = _field(candidates[0], "name", "candidate", default="n/a") if candidates else "n/a"
    return text["summary"].format(
        candidate_count=len(candidates),
        top_candidate=_clean_text(top_candidate),
        trial_count=len(trials),
    )


def _candidate_row(rank: int, candidate: Mapping[str, Any]) -> str:
    name = _field(candidate, "name", "candidate", "id")
    mechanism = _field(candidate, "mechanism", "target", default="n/a")
    score = _field(candidate, "score", "composite_score", "rank_score", default="n/a")
    safety = _field(candidate, "safety", "safety_score", default="n/a")
    evidence = _field(candidate, "evidence", "evidence_level", default="n/a")
    recommendation = _field(candidate, "recommendation", "decision", default="n/a")
    return _table_row([rank, name, mechanism, score, safety, evidence, recommendation])


def _trial_row(trial: Mapping[str, Any]) -> str:
    trial_name = _field(trial, "trial", "name", "id")
    phase = _field(trial, "phase", default="n/a")
    population = _field(trial, "population", "cohort", default="n/a")
    duration = _field(trial, "duration", "follow_up", default="n/a")
    endpoint = _field(trial, "primary_endpoint", "endpoint", default="n/a")
    outcome = _field(trial, "outcome", "summary", default="n/a")
    return _table_row([trial_name, phase, population, duration, endpoint, outcome])


def _table_row(values: Sequence[Any]) -> str:
    cells = [_escape_markdown_cell(_format_value(value)) for value in values]
    return "| " + " | ".join(cells) + " |"


def _field(mapping: Mapping[str, Any], *names: str, default: Any = "n/a") -> Any:
    for name in names:
        value = mapping.get(name)
        if value is not None and value != "":
            return value
    return default


def _format_value(value: Any) -> str:
    if value is None or value == "":
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3g}"
    if isinstance(value, (list, tuple, set)):
        return ", ".join(_format_value(item) for item in value) or "n/a"
    return str(value)


def _clean_text(value: Any) -> str:
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def _escape_markdown_cell(value: str) -> str:
    return _clean_text(value).replace("|", r"\|")


def _as_list(value: Any, field_name: str) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValueError(f"{field_name}[{index}] must be an object")
    return value


def _optional_string(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _labels(language: str) -> dict[str, str]:
    if language.lower().startswith("zh"):
        return {
            "generated": "生成日期",
            "summary_heading": "执行摘要",
            "candidates_heading": "候选药排名",
            "trials_heading": "虚拟试验摘要",
            "limits_heading": "解释边界",
            "rank": "排名",
            "candidate": "候选药",
            "mechanism": "机制",
            "score": "评分",
            "safety": "安全性",
            "evidence": "证据",
            "recommendation": "建议",
            "trial": "试验",
            "phase": "阶段",
            "population": "人群",
            "duration": "周期",
            "endpoint": "主要终点",
            "outcome": "结果",
            "no_candidates": "未提供候选药排名。",
            "no_trials": "未提供虚拟试验摘要。",
            "empty_summary": "本次模拟没有产生候选药排名或试验摘要。",
            "summary": "本次模拟共评估 {candidate_count} 个候选药，当前领先候选药为 {top_candidate}，并汇总了 {trial_count} 个虚拟试验场景。",
            "limit_scores": "评分是模拟输出，不等同于临床证据。",
            "limit_rankings": "候选药排名仅用于研发优先级判断，仍需要进一步实验验证。",
            "limit_trials": "虚拟试验摘要仅描述原型场景，不能用于医疗决策。",
        }
    return {
        "generated": "Generated",
        "summary_heading": "Executive Summary",
        "candidates_heading": "Ranked Candidates",
        "trials_heading": "Trial Summaries",
        "limits_heading": "Interpretation Limits",
        "rank": "Rank",
        "candidate": "Candidate",
        "mechanism": "Mechanism",
        "score": "Score",
        "safety": "Safety",
        "evidence": "Evidence",
        "recommendation": "Recommendation",
        "trial": "Trial",
        "phase": "Phase",
        "population": "Population",
        "duration": "Duration",
        "endpoint": "Primary Endpoint",
        "outcome": "Outcome",
        "no_candidates": "No ranked candidates were provided.",
        "no_trials": "No trial summaries were provided.",
        "empty_summary": "The simulation did not produce candidate rankings or trial summaries.",
        "summary": "The simulation ranked {candidate_count} candidate(s), identified {top_candidate} as the current lead, and summarized {trial_count} trial scenario(s).",
        "limit_scores": "Scores are simulation outputs, not clinical evidence.",
        "limit_rankings": "Candidate rankings should be treated as prioritization hints for further validation.",
        "limit_trials": "Trial summaries describe prototype scenarios and must not be used for medical decisions.",
    }


if __name__ == "__main__":
    raise SystemExit(main())
