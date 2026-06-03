"""SQLite-backed molecule library for Asclepius.

The library stores compounds by SMILES/name, optional external identifiers, and
JSON analysis payloads produced by the molecular workflow.  It intentionally
uses only the Python standard library so it can run in the desktop prototype
without additional services or chemistry packages.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SEED_CSV = ROOT_DIR / "data" / "sample_molecules.csv"


@dataclass(frozen=True)
class Compound:
    """A stored molecule entry."""

    compound_id: int
    name: str
    smiles: str
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class Analysis:
    """A JSON analysis payload associated with a compound."""

    analysis_id: int
    compound_id: int
    analysis_type: str
    payload: dict[str, Any]
    created_at: str = ""


class MoleculeLibrary:
    """Small SQLite molecule library with schema initialization on open."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        if self.db_path != Path(":memory:"):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(db_path))
        self.connection.row_factory = sqlite3.Row
        initialize_schema(self.connection)

    def close(self) -> None:
        """Close the underlying SQLite connection."""

        self.connection.close()

    def __enter__(self) -> "MoleculeLibrary":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def upsert_compound(self, name: str, smiles: str, notes: str = "") -> Compound:
        """Insert or update a compound, matching existing rows by SMILES or name."""

        return upsert_compound(self.connection, name=name, smiles=smiles, notes=notes)

    def import_csv(self, csv_path: str | Path) -> int:
        """Import name/smiles/notes rows from a CSV file."""

        return import_compounds_csv(self.connection, csv_path)

    def import_seed(self, csv_path: str | Path = DEFAULT_SEED_CSV) -> int:
        """Import bundled sample molecules."""

        return import_seed_library(self.connection, csv_path)

    def list_compounds(self, limit: int | None = None) -> list[Compound]:
        """Return compounds ordered by name."""

        return list_compounds(self.connection, limit=limit)

    def search_compounds(self, query: str, limit: int | None = None) -> list[Compound]:
        """Search compounds by name, SMILES, or notes."""

        return search_compounds(self.connection, query=query, limit=limit)

    def store_analysis(
        self,
        compound_id: int,
        analysis: dict[str, Any],
        analysis_type: str = "molecular_workflow",
    ) -> Analysis:
        """Store a JSON-serializable analysis payload for a compound."""

        return store_analysis(
            self.connection,
            compound_id=compound_id,
            analysis=analysis,
            analysis_type=analysis_type,
        )

    def list_analyses(
        self,
        compound_id: int,
        analysis_type: str | None = None,
    ) -> list[Analysis]:
        """Return analyses for one compound, newest first."""

        return list_analyses(self.connection, compound_id=compound_id, analysis_type=analysis_type)

    def add_external_id(self, compound_id: int, source: str, external_id: str) -> None:
        """Attach or replace an external identifier for a compound."""

        add_external_id(self.connection, compound_id=compound_id, source=source, external_id=external_id)

    def list_external_ids(self, compound_id: int) -> dict[str, str]:
        """Return external identifiers keyed by source."""

        return list_external_ids(self.connection, compound_id=compound_id)


def open_library(db_path: str | Path) -> MoleculeLibrary:
    """Create or open an Asclepius molecule library database."""

    return MoleculeLibrary(db_path)


def initialize_schema(connection: sqlite3.Connection) -> None:
    """Create the molecule library tables and indexes if they do not exist."""

    connection.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS compounds (
            compound_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE,
            smiles TEXT NOT NULL COLLATE NOCASE,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(smiles),
            UNIQUE(name)
        );

        CREATE TABLE IF NOT EXISTS analyses (
            analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
            compound_id INTEGER NOT NULL,
            analysis_type TEXT NOT NULL DEFAULT 'molecular_workflow',
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(compound_id) REFERENCES compounds(compound_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS external_ids (
            external_id_row INTEGER PRIMARY KEY AUTOINCREMENT,
            compound_id INTEGER NOT NULL,
            source TEXT NOT NULL COLLATE NOCASE,
            external_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(compound_id) REFERENCES compounds(compound_id) ON DELETE CASCADE,
            UNIQUE(compound_id, source)
        );

        CREATE INDEX IF NOT EXISTS idx_compounds_name ON compounds(name);
        CREATE INDEX IF NOT EXISTS idx_compounds_smiles ON compounds(smiles);
        CREATE INDEX IF NOT EXISTS idx_analyses_compound ON analyses(compound_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_external_ids_source ON external_ids(source, external_id);
        """
    )
    connection.commit()


def upsert_compound(
    connection: sqlite3.Connection,
    *,
    name: str,
    smiles: str,
    notes: str = "",
) -> Compound:
    """Insert or update a compound, matching an existing row by SMILES first, then name."""

    name = _required_text(name, "name")
    smiles = _required_text(smiles, "smiles")
    notes = (notes or "").strip()

    row = connection.execute(
        "SELECT * FROM compounds WHERE lower(smiles) = lower(?) OR lower(name) = lower(?) "
        "ORDER BY CASE WHEN lower(smiles) = lower(?) THEN 0 ELSE 1 END, compound_id LIMIT 1",
        (smiles, name, smiles),
    ).fetchone()

    if row is None:
        cursor = connection.execute(
            "INSERT INTO compounds (name, smiles, notes) VALUES (?, ?, ?)",
            (name, smiles, notes),
        )
        connection.commit()
        return _get_compound(connection, int(cursor.lastrowid))

    connection.execute(
        """
        UPDATE compounds
           SET name = ?,
               smiles = ?,
               notes = ?,
               updated_at = CURRENT_TIMESTAMP
         WHERE compound_id = ?
        """,
        (name, smiles, notes, row["compound_id"]),
    )
    connection.commit()
    return _get_compound(connection, int(row["compound_id"]))


def import_compounds_csv(connection: sqlite3.Connection, csv_path: str | Path) -> int:
    """Import compounds from a CSV file with name, smiles, and optional notes columns."""

    path = Path(csv_path)
    imported = 0
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        _ensure_columns(reader.fieldnames, ("name", "smiles"))
        for row in reader:
            upsert_compound(
                connection,
                name=row.get("name", ""),
                smiles=row.get("smiles", ""),
                notes=row.get("notes", ""),
            )
            imported += 1
    return imported


def import_seed_library(
    connection: sqlite3.Connection,
    csv_path: str | Path = DEFAULT_SEED_CSV,
) -> int:
    """Import the bundled Asclepius sample molecule CSV."""

    return import_compounds_csv(connection, csv_path)


def list_compounds(connection: sqlite3.Connection, limit: int | None = None) -> list[Compound]:
    """List compounds ordered by case-insensitive name."""

    sql = "SELECT * FROM compounds ORDER BY lower(name), compound_id"
    params: tuple[int, ...] = ()
    if limit is not None:
        sql += " LIMIT ?"
        params = (_positive_limit(limit),)
    rows = connection.execute(sql, params).fetchall()
    return [_compound_from_row(row) for row in rows]


def search_compounds(
    connection: sqlite3.Connection,
    *,
    query: str,
    limit: int | None = None,
) -> list[Compound]:
    """Search compounds by name, SMILES, or notes."""

    query = (query or "").strip()
    if not query:
        return list_compounds(connection, limit=limit)

    sql = (
        "SELECT * FROM compounds "
        "WHERE lower(name) LIKE lower(?) OR lower(smiles) LIKE lower(?) OR lower(notes) LIKE lower(?) "
        "ORDER BY lower(name), compound_id"
    )
    params: tuple[str, ...] | tuple[str, str, str, int]
    pattern = f"%{query}%"
    params = (pattern, pattern, pattern)
    if limit is not None:
        sql += " LIMIT ?"
        params = (pattern, pattern, pattern, _positive_limit(limit))
    rows = connection.execute(sql, params).fetchall()
    return [_compound_from_row(row) for row in rows]


def store_analysis(
    connection: sqlite3.Connection,
    *,
    compound_id: int,
    analysis: dict[str, Any],
    analysis_type: str = "molecular_workflow",
) -> Analysis:
    """Store a JSON-serializable analysis payload for a compound."""

    _get_compound(connection, compound_id)
    analysis_type = _required_text(analysis_type, "analysis_type")
    payload_json = json.dumps(analysis, ensure_ascii=False, sort_keys=True)
    cursor = connection.execute(
        "INSERT INTO analyses (compound_id, analysis_type, payload_json) VALUES (?, ?, ?)",
        (compound_id, analysis_type, payload_json),
    )
    connection.commit()
    return _get_analysis(connection, int(cursor.lastrowid))


def list_analyses(
    connection: sqlite3.Connection,
    *,
    compound_id: int,
    analysis_type: str | None = None,
) -> list[Analysis]:
    """List analyses for one compound, newest first."""

    _get_compound(connection, compound_id)
    if analysis_type is None:
        rows = connection.execute(
            "SELECT * FROM analyses WHERE compound_id = ? ORDER BY analysis_id DESC",
            (compound_id,),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT * FROM analyses WHERE compound_id = ? AND analysis_type = ? ORDER BY analysis_id DESC",
            (compound_id, analysis_type),
        ).fetchall()
    return [_analysis_from_row(row) for row in rows]


def add_external_id(
    connection: sqlite3.Connection,
    *,
    compound_id: int,
    source: str,
    external_id: str,
) -> None:
    """Attach or replace an external identifier for a compound."""

    _get_compound(connection, compound_id)
    source = _required_text(source, "source")
    external_id = _required_text(external_id, "external_id")
    connection.execute(
        """
        INSERT INTO external_ids (compound_id, source, external_id)
        VALUES (?, ?, ?)
        ON CONFLICT(compound_id, source)
        DO UPDATE SET external_id = excluded.external_id
        """,
        (compound_id, source, external_id),
    )
    connection.commit()


def list_external_ids(connection: sqlite3.Connection, *, compound_id: int) -> dict[str, str]:
    """Return external identifiers for a compound keyed by source."""

    _get_compound(connection, compound_id)
    rows = connection.execute(
        "SELECT source, external_id FROM external_ids WHERE compound_id = ? ORDER BY lower(source)",
        (compound_id,),
    ).fetchall()
    return {row["source"]: row["external_id"] for row in rows}


def _get_compound(connection: sqlite3.Connection, compound_id: int) -> Compound:
    row = connection.execute("SELECT * FROM compounds WHERE compound_id = ?", (compound_id,)).fetchone()
    if row is None:
        raise KeyError(f"unknown compound_id: {compound_id}")
    return _compound_from_row(row)


def _get_analysis(connection: sqlite3.Connection, analysis_id: int) -> Analysis:
    row = connection.execute("SELECT * FROM analyses WHERE analysis_id = ?", (analysis_id,)).fetchone()
    if row is None:
        raise KeyError(f"unknown analysis_id: {analysis_id}")
    return _analysis_from_row(row)


def _compound_from_row(row: sqlite3.Row) -> Compound:
    return Compound(
        compound_id=int(row["compound_id"]),
        name=row["name"],
        smiles=row["smiles"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _analysis_from_row(row: sqlite3.Row) -> Analysis:
    return Analysis(
        analysis_id=int(row["analysis_id"]),
        compound_id=int(row["compound_id"]),
        analysis_type=row["analysis_type"],
        payload=json.loads(row["payload_json"]),
        created_at=row["created_at"],
    )


def _required_text(value: str, field_name: str) -> str:
    text = (value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def _ensure_columns(fieldnames: Iterable[str] | None, required: Iterable[str]) -> None:
    actual = set(fieldnames or ())
    missing = [column for column in required if column not in actual]
    if missing:
        raise ValueError(f"CSV missing required columns: {', '.join(missing)}")


def _positive_limit(limit: int) -> int:
    if limit < 1:
        raise ValueError("limit must be positive")
    return limit
