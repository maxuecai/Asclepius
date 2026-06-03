"""Data loading primitives for the geroscience drug simulation prototype.

CSV schemas
-----------
Hallmarks:
    hallmark_id,name,weight,description

Candidates:
    candidate_id,name,target_hallmarks,expression_reversal,safety,
    translational_evidence,trial_feasibility,regulatory_readiness,
    biomarker_relevance,evidence_sources,mechanism,notes

Evidence sources:
    source_id,title,evidence_type,source,year,url,quality,notes

Trial endpoints:
    endpoint_id,name,category,importance,description

Scores are normalized floats in the inclusive range [0.0, 1.0].
``target_hallmarks`` is a semicolon-separated list of hallmark IDs.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


HALLMARK_COLUMNS = ("hallmark_id", "name", "weight", "description")
CANDIDATE_COLUMNS = (
    "candidate_id",
    "name",
    "target_hallmarks",
    "expression_reversal",
    "safety",
    "translational_evidence",
    "trial_feasibility",
    "regulatory_readiness",
    "biomarker_relevance",
    "evidence_sources",
    "mechanism",
    "notes",
)
EVIDENCE_COLUMNS = (
    "source_id",
    "title",
    "evidence_type",
    "source",
    "year",
    "url",
    "quality",
    "notes",
)
ENDPOINT_COLUMNS = ("endpoint_id", "name", "category", "importance", "description")
SOFTWARE_COLUMNS = ("tool_id", "name", "category", "role", "url", "integration_status", "notes")


@dataclass(frozen=True)
class AgingHallmark:
    """A weighted aging hallmark that drug candidates may target."""

    hallmark_id: str
    name: str
    weight: float
    description: str = ""


@dataclass(frozen=True)
class CandidateDrug:
    """A candidate intervention with normalized evidence inputs."""

    candidate_id: str
    name: str
    target_hallmarks: tuple[str, ...]
    expression_reversal: float
    safety: float
    translational_evidence: float
    trial_feasibility: float
    regulatory_readiness: float = 0.5
    biomarker_relevance: float = 0.5
    evidence_sources: tuple[str, ...] = ()
    mechanism: str = ""
    notes: str = ""


@dataclass(frozen=True)
class EvidenceSource:
    """A source supporting a candidate, endpoint, or modeling assumption."""

    source_id: str
    title: str
    evidence_type: str
    source: str
    year: int
    url: str
    quality: float
    notes: str = ""


@dataclass(frozen=True)
class TrialEndpoint:
    """A clinically meaningful or exploratory endpoint for virtual trials."""

    endpoint_id: str
    name: str
    category: str
    importance: float
    description: str = ""


@dataclass(frozen=True)
class SoftwareTool:
    """A software or external data source relevant to the molecular workflow."""

    tool_id: str
    name: str
    category: str
    role: str
    url: str
    integration_status: str
    notes: str = ""


def load_hallmarks(path: str | Path) -> list[AgingHallmark]:
    """Load aging hallmarks from a CSV file."""

    rows = _read_rows(path, HALLMARK_COLUMNS)
    hallmarks = [
        AgingHallmark(
            hallmark_id=_required(row, "hallmark_id"),
            name=_required(row, "name"),
            weight=_bounded_float(row, "weight"),
            description=row.get("description", "").strip(),
        )
        for row in rows
    ]
    _ensure_unique("hallmark_id", [hallmark.hallmark_id for hallmark in hallmarks])
    return hallmarks


def load_candidates(path: str | Path) -> list[CandidateDrug]:
    """Load candidate drugs from a CSV file."""

    rows = _read_rows(path, CANDIDATE_COLUMNS)
    candidates = [
        CandidateDrug(
            candidate_id=_required(row, "candidate_id"),
            name=_required(row, "name"),
            target_hallmarks=_split_ids(row.get("target_hallmarks", "")),
            expression_reversal=_bounded_float(row, "expression_reversal"),
            safety=_bounded_float(row, "safety"),
            translational_evidence=_bounded_float(row, "translational_evidence"),
            trial_feasibility=_bounded_float(row, "trial_feasibility"),
            regulatory_readiness=_bounded_float(row, "regulatory_readiness"),
            biomarker_relevance=_bounded_float(row, "biomarker_relevance"),
            evidence_sources=_split_optional_ids(row.get("evidence_sources", "")),
            mechanism=row.get("mechanism", "").strip(),
            notes=row.get("notes", "").strip(),
        )
        for row in rows
    ]
    _ensure_unique("candidate_id", [candidate.candidate_id for candidate in candidates])
    return candidates


def load_candidate_drugs(path: str | Path) -> list[CandidateDrug]:
    """Compatibility alias for callers that use the fuller domain phrase."""

    return load_candidates(path)


def load_evidence_sources(path: str | Path) -> list[EvidenceSource]:
    """Load curated evidence sources from a CSV file."""

    rows = _read_rows(path, EVIDENCE_COLUMNS)
    sources = [
        EvidenceSource(
            source_id=_required(row, "source_id"),
            title=_required(row, "title"),
            evidence_type=_required(row, "evidence_type"),
            source=_required(row, "source"),
            year=_int_field(row, "year"),
            url=_required(row, "url"),
            quality=_bounded_float(row, "quality"),
            notes=row.get("notes", "").strip(),
        )
        for row in rows
    ]
    _ensure_unique("source_id", [source.source_id for source in sources])
    return sources


def load_trial_endpoints(path: str | Path) -> list[TrialEndpoint]:
    """Load recommended virtual-trial endpoint definitions."""

    rows = _read_rows(path, ENDPOINT_COLUMNS)
    endpoints = [
        TrialEndpoint(
            endpoint_id=_required(row, "endpoint_id"),
            name=_required(row, "name"),
            category=_required(row, "category"),
            importance=_bounded_float(row, "importance"),
            description=row.get("description", "").strip(),
        )
        for row in rows
    ]
    _ensure_unique("endpoint_id", [endpoint.endpoint_id for endpoint in endpoints])
    return endpoints


def load_software_tools(path: str | Path) -> list[SoftwareTool]:
    """Load curated software and external-resource metadata."""

    rows = _read_rows(path, SOFTWARE_COLUMNS)
    tools = [
        SoftwareTool(
            tool_id=_required(row, "tool_id"),
            name=_required(row, "name"),
            category=_required(row, "category"),
            role=_required(row, "role"),
            url=_required(row, "url"),
            integration_status=_required(row, "integration_status"),
            notes=row.get("notes", "").strip(),
        )
        for row in rows
    ]
    _ensure_unique("tool_id", [tool.tool_id for tool in tools])
    return tools


def hallmarks_by_id(hallmarks: Iterable[AgingHallmark]) -> dict[str, AgingHallmark]:
    """Return hallmarks keyed by ID, rejecting duplicates."""

    hallmark_list = list(hallmarks)
    indexed = {hallmark.hallmark_id: hallmark for hallmark in hallmark_list}
    if len(indexed) != len(hallmark_list):
        raise ValueError("Duplicate hallmark_id values are not allowed")
    return indexed


def _read_rows(path: str | Path, required_columns: tuple[str, ...]) -> list[dict[str, str]]:
    csv_path = Path(path)
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in required_columns if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{csv_path} is missing required columns: {', '.join(missing)}")
        return list(reader)


def _required(row: dict[str, str], field: str) -> str:
    value = row.get(field, "").strip()
    if not value:
        raise ValueError(f"Field {field!r} is required")
    return value


def _bounded_float(row: dict[str, str], field: str) -> float:
    raw_value = _required(row, field)
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ValueError(f"Field {field!r} must be a float") from exc
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"Field {field!r} must be between 0.0 and 1.0")
    return value


def _split_ids(value: str) -> tuple[str, ...]:
    ids = tuple(part.strip() for part in value.split(";") if part.strip())
    if not ids:
        raise ValueError("Field 'target_hallmarks' must contain at least one hallmark ID")
    return ids


def _split_optional_ids(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(";") if part.strip())


def _int_field(row: dict[str, str], field: str) -> int:
    raw_value = _required(row, field)
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"Field {field!r} must be an integer") from exc


def _ensure_unique(field: str, values: list[str]) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"Duplicate {field} values are not allowed")
