"""Optional stdlib-only clients for external chemistry data sources.

The helpers in this module are deliberately explicit: URL builders and parsers
are pure, and network access only happens through ``fetch_json`` or the small
``fetch_*`` wrappers that require a timeout.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT_SECONDS = 10.0

PUBCHEM_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
CHEMBL_BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"
BINDINGDB_BASE_URL = "https://www.bindingdb.org/rwd/bind/chemsearch/marvin"
RCSB_BASE_URL = "https://data.rcsb.org/rest/v1/core"


@dataclass(frozen=True)
class PubChemCompound:
    """Minimal PubChem compound identity and structure fields."""

    cid: int | None
    canonical_smiles: str = ""
    isomeric_smiles: str = ""
    inchikey: str = ""


@dataclass(frozen=True)
class ChemblResult:
    """Small normalized ChEMBL activity or similarity result."""

    molecule_chembl_id: str = ""
    molecule_name: str = ""
    similarity: str = ""
    target_chembl_id: str = ""
    target_name: str = ""
    activity_type: str = ""
    activity_value: str = ""
    activity_units: str = ""
    pchembl_value: str = ""


UrlOpener = Callable[..., Any]


def build_pubchem_name_property_url(name: str) -> str:
    """Build a PubChem PUG-REST URL for CID, SMILES, and InChIKey by name."""

    cleaned = _required_text(name, "name")
    properties = "CanonicalSMILES,IsomericSMILES,InChIKey"
    return f"{PUBCHEM_BASE_URL}/compound/name/{quote(cleaned, safe='')}/property/{properties}/JSON"


def parse_pubchem_compounds(payload: dict[str, Any]) -> list[PubChemCompound]:
    """Parse PubChem property JSON into minimal compound records."""

    properties = payload.get("PropertyTable", {}).get("Properties", [])
    if not isinstance(properties, list):
        return []

    compounds: list[PubChemCompound] = []
    for item in properties:
        if not isinstance(item, dict):
            continue
        compounds.append(
            PubChemCompound(
                cid=_optional_int(item.get("CID")),
                canonical_smiles=str(item.get("CanonicalSMILES", "") or ""),
                isomeric_smiles=str(item.get("IsomericSMILES", "") or ""),
                inchikey=str(item.get("InChIKey", "") or ""),
            )
        )
    return compounds


def fetch_pubchem_name(name: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> list[PubChemCompound]:
    """Fetch and parse PubChem compound properties for a name."""

    return parse_pubchem_compounds(fetch_json(build_pubchem_name_property_url(name), timeout=timeout))


def build_chembl_similarity_url(smiles: str, similarity_cutoff: int = 70) -> str:
    """Build a ChEMBL similarity-search URL for a SMILES query."""

    cleaned = _required_text(smiles, "smiles")
    cutoff = int(similarity_cutoff)
    if cutoff < 0 or cutoff > 100:
        raise ValueError("similarity_cutoff must be between 0 and 100")
    return f"{CHEMBL_BASE_URL}/similarity/{quote(cleaned, safe='')}/{cutoff}.json"


def parse_chembl_results(payload: dict[str, Any]) -> list[ChemblResult]:
    """Parse minimal ChEMBL similarity or activity-like JSON results."""

    raw_items = payload.get("molecules")
    if not isinstance(raw_items, list):
        raw_items = payload.get("activities")
    if not isinstance(raw_items, list):
        return []

    results: list[ChemblResult] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        molecule_structures = item.get("molecule_structures") if isinstance(item.get("molecule_structures"), dict) else {}
        results.append(
            ChemblResult(
                molecule_chembl_id=str(item.get("molecule_chembl_id", "") or ""),
                molecule_name=str(item.get("pref_name", item.get("molecule_pref_name", "")) or ""),
                similarity=str(item.get("similarity", item.get("molecule_similarity", "")) or ""),
                target_chembl_id=str(item.get("target_chembl_id", "") or ""),
                target_name=str(item.get("target_pref_name", item.get("target_organism", "")) or ""),
                activity_type=str(item.get("standard_type", item.get("type", "")) or ""),
                activity_value=str(item.get("standard_value", item.get("value", "")) or ""),
                activity_units=str(item.get("standard_units", item.get("units", "")) or ""),
                pchembl_value=str(item.get("pchembl_value", "") or ""),
            )
        )
        if molecule_structures and not results[-1].molecule_name:
            results[-1] = ChemblResult(
                molecule_chembl_id=results[-1].molecule_chembl_id,
                molecule_name=str(molecule_structures.get("canonical_smiles", "") or ""),
                similarity=results[-1].similarity,
                target_chembl_id=results[-1].target_chembl_id,
                target_name=results[-1].target_name,
                activity_type=results[-1].activity_type,
                activity_value=results[-1].activity_value,
                activity_units=results[-1].activity_units,
                pchembl_value=results[-1].pchembl_value,
            )
    return results


def fetch_chembl_similarity(
    smiles: str,
    similarity_cutoff: int = 70,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> list[ChemblResult]:
    """Fetch and parse ChEMBL similarity results for a SMILES query."""

    url = build_chembl_similarity_url(smiles, similarity_cutoff=similarity_cutoff)
    return parse_chembl_results(fetch_json(url, timeout=timeout))


def build_bindingdb_ligand_url(ligand_id: str | int) -> str:
    """Build a BindingDB ligand-detail URL from a BindingDB monomer id."""

    cleaned = _required_text(str(ligand_id), "ligand_id")
    return f"{BINDINGDB_BASE_URL}/MolStructure.jsp?{urlencode({'monomerid': cleaned})}"


def build_rcsb_entry_url(pdb_id: str) -> str:
    """Build an RCSB PDB core-entry API URL."""

    cleaned = _required_text(pdb_id, "pdb_id").upper()
    return f"{RCSB_BASE_URL}/entry/{quote(cleaned, safe='')}"


def fetch_json(
    url: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    opener: UrlOpener = urlopen,
) -> dict[str, Any]:
    """Fetch JSON with an explicit timeout and a conservative User-Agent."""

    if timeout <= 0:
        raise ValueError("timeout must be positive")
    request = Request(
        _required_text(url, "url"),
        headers={"Accept": "application/json", "User-Agent": "asclepius/0.1 stdlib-client"},
    )
    with opener(request, timeout=timeout) as response:
        data = response.read()
    parsed = json.loads(data.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("expected a JSON object")
    return parsed


def summarize_external_status() -> str:
    """Summarize configured optional external sources and network behavior."""

    sources = (
        ("PubChem", PUBCHEM_BASE_URL, "name-to-property lookup"),
        ("ChEMBL", CHEMBL_BASE_URL, "SMILES similarity and activity-like parsing"),
        ("BindingDB", BINDINGDB_BASE_URL, "ligand detail URL construction"),
        ("RCSB PDB", RCSB_BASE_URL, "PDB entry lookup"),
    )
    lines = [
        "External chemistry sources are configured as optional public endpoints.",
        f"Network calls are opt-in through fetch helpers and default to {DEFAULT_TIMEOUT_SECONDS:.0f}s timeouts.",
    ]
    lines.extend(f"- {name}: {purpose} ({base_url})" for name, base_url, purpose in sources)
    return "\n".join(lines)


def _required_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required")
    return cleaned


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
