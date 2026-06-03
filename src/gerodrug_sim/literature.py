"""Literature radar and lightweight evidence extraction for Asclepius."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any, Callable, Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_RESEARCH_DB = ROOT_DIR / "data" / "asclepius_research.sqlite"
PUBMED_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DEFAULT_TIMEOUT_SECONDS = 12.0


@dataclass(frozen=True)
class Paper:
    """A normalized literature record."""

    pmid: str
    title: str
    abstract: str
    journal: str = ""
    year: int = 0
    doi: str = ""
    url: str = ""
    authors: tuple[str, ...] = ()


@dataclass(frozen=True)
class PaperSignals:
    """Rule-extracted R&D signals from title/abstract text."""

    categories: tuple[str, ...]
    interventions: tuple[str, ...]
    matched_factors: tuple[str, ...]
    tissues: tuple[str, ...]
    models: tuple[str, ...]
    readouts: tuple[str, ...]
    safety_risks: tuple[str, ...]
    evidence_level: str
    evidence_score: float


@dataclass(frozen=True)
class StoredPaper:
    """A paper stored in the local research library."""

    paper_id: int
    pmid: str
    title: str
    abstract: str
    journal: str
    year: int
    doi: str
    url: str
    signals: PaperSignals
    created_at: str = ""
    updated_at: str = ""


UrlOpener = Callable[..., Any]


def build_pubmed_search_url(query: str, retmax: int = 20) -> str:
    """Build a PubMed ESearch URL returning JSON IDs."""

    cleaned = _required_text(query, "query")
    max_rows = max(1, min(int(retmax), 200))
    params = urlencode(
        {
            "db": "pubmed",
            "term": cleaned,
            "retmode": "json",
            "retmax": max_rows,
            "sort": "pub+date",
        }
    )
    return f"{PUBMED_EUTILS}/esearch.fcgi?{params}"


def build_pubmed_fetch_url(pmids: Iterable[str]) -> str:
    """Build a PubMed EFetch URL for XML records."""

    ids = [str(pmid).strip() for pmid in pmids if str(pmid).strip()]
    if not ids:
        raise ValueError("At least one PMID is required")
    params = urlencode({"db": "pubmed", "id": ",".join(ids), "retmode": "xml"})
    return f"{PUBMED_EUTILS}/efetch.fcgi?{params}"


def parse_pubmed_search_ids(payload: dict[str, Any]) -> list[str]:
    """Parse ESearch JSON into PMID strings."""

    ids = payload.get("esearchresult", {}).get("idlist", [])
    if not isinstance(ids, list):
        return []
    return [str(item) for item in ids if str(item).strip()]


def fetch_pubmed_json(
    url: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    opener: UrlOpener = urlopen,
) -> dict[str, Any]:
    """Fetch a PubMed JSON response with explicit timeout."""

    request = Request(
        _required_text(url, "url"),
        headers={"Accept": "application/json", "User-Agent": "asclepius-literature/0.1"},
    )
    with opener(request, timeout=timeout) as response:
        data = response.read()
    parsed = json.loads(data.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("expected PubMed JSON object")
    return parsed


def fetch_pubmed_xml(
    url: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    opener: UrlOpener = urlopen,
) -> str:
    """Fetch a PubMed XML response with explicit timeout."""

    request = Request(
        _required_text(url, "url"),
        headers={"Accept": "application/xml", "User-Agent": "asclepius-literature/0.1"},
    )
    with opener(request, timeout=timeout) as response:
        data = response.read()
    return data.decode("utf-8")


def fetch_pubmed_records(
    query: str,
    retmax: int = 20,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    opener: UrlOpener = urlopen,
) -> list[Paper]:
    """Search PubMed and fetch normalized records."""

    ids = parse_pubmed_search_ids(fetch_pubmed_json(build_pubmed_search_url(query, retmax), timeout=timeout, opener=opener))
    if not ids:
        return []
    return parse_pubmed_xml(fetch_pubmed_xml(build_pubmed_fetch_url(ids), timeout=timeout, opener=opener))


def parse_pubmed_xml(xml_text: str) -> list[Paper]:
    """Parse PubMed EFetch XML into Paper records."""

    root = ET.fromstring(xml_text)
    papers: list[Paper] = []
    for article in root.findall(".//PubmedArticle"):
        pmid = _text(article.find(".//PMID"))
        if not pmid:
            continue
        title = _join_text(article.find(".//ArticleTitle"))
        abstract = "\n".join(
            part for part in (_join_text(item) for item in article.findall(".//Abstract/AbstractText")) if part
        )
        journal = _text(article.find(".//Journal/Title")) or _text(article.find(".//ISOAbbreviation"))
        year = _publication_year(article)
        doi = _article_doi(article)
        authors = tuple(
            name
            for name in (
                _author_name(author)
                for author in article.findall(".//AuthorList/Author")
            )
            if name
        )
        papers.append(
            Paper(
                pmid=pmid,
                title=title,
                abstract=abstract,
                journal=journal,
                year=year,
                doi=doi,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                authors=authors,
            )
        )
    return papers


def analyze_paper_signals(paper: Paper | str) -> PaperSignals:
    """Extract coarse R&D signals from a paper title/abstract."""

    text = paper if isinstance(paper, str) else f"{paper.title}\n{paper.abstract}"
    lowered = text.lower()
    interventions = _matches(
        lowered,
        {
            "OSK": ("osk", "oct4 sox2 klf4", "yamanaka"),
            "OSKM": ("oskm", "oct4 sox2 klf4 c-myc", "c-myc"),
            "partial reprogramming": ("partial reprogramming", "cellular reprogramming"),
            "senolytic": ("senolytic", "senolytics", "dasatinib", "quercetin", "fisetin"),
            "mTOR": ("mtor", "rapamycin", "everolimus"),
            "NAD": ("nad+", "nmn", "nicotinamide riboside"),
            "CRISPR": ("crispr", "dcas9", "base editor", "prime editor"),
            "mRNA": ("mrna", "messenger rna"),
            "AAV": ("aav", "adeno-associated"),
        },
    )
    tissues = _matches(
        lowered,
        {
            "retina/optic nerve": ("retina", "retinal", "optic nerve", "vision"),
            "brain/neuron": ("brain", "neuron", "neuronal", "dentate gyrus", "memory"),
            "skin/fibroblast": ("skin", "fibroblast", "dermal", "wound"),
            "muscle": ("muscle", "myofiber", "sarcopenia"),
            "immune/blood": ("immune", "t cell", "hematopoietic", "blood"),
            "liver": ("liver", "hepatic", "hepatocyte"),
        },
    )
    models = _matches(
        lowered,
        {
            "in vitro": ("in vitro", "cell culture", "fibroblast"),
            "mouse": ("mouse", "mice", "murine"),
            "human": ("human", "patient", "clinical"),
            "non-human primate": ("primate", "monkey", "macaque"),
            "organoid": ("organoid", "organ-on-chip"),
        },
    )
    readouts = _matches(
        lowered,
        {
            "DNA methylation age": ("methylation age", "epigenetic clock", "dna methylation"),
            "RNA-seq": ("rna-seq", "transcriptome", "gene expression"),
            "ATAC/chromatin": ("atac", "chromatin", "histone"),
            "single-cell": ("single-cell", "single cell", "scrna"),
            "function": ("function", "restore", "regeneration", "memory", "vision"),
        },
    )
    safety_risks = _matches(
        lowered,
        {
            "oncogenic risk": ("oncogenic", "cancer", "tumor", "tumour", "teratoma"),
            "dedifferentiation": ("dedifferentiation", "pluripotency", "loss of identity"),
            "immune response": ("immune response", "immunogenicity", "inflammation"),
            "off-target": ("off-target", "toxicity", "adverse"),
        },
    )
    matched_factors = _matches(
        lowered,
        {
            "osk": ("osk", "oct4 sox2 klf4", "yamanaka"),
            "oskm": ("oskm", "oct4 sox2 klf4 c-myc", "c-myc"),
            "oct4": ("oct4", "pou5f1"),
            "sox2": ("sox2",),
            "klf4": ("klf4",),
            "myc": ("myc", "c-myc"),
            "sirt6": ("sirt6",),
            "tet2": ("tet2",),
            "lin28a": ("lin28a", "lin28"),
            "foxo3": ("foxo3", "foxo3a"),
        },
    )
    categories = _matches(
        lowered,
        {
            "partial reprogramming": ("partial reprogramming", "yamanaka", "osk", "oskm"),
            "senolytics": ("senolytic", "senescence", "senescent cell"),
            "gene delivery": ("aav", "mrna", "lnp", "gene therapy", "delivery"),
            "epigenetic aging": ("epigenetic", "methylation", "chromatin"),
        },
    )
    return PaperSignals(
        categories=tuple(categories or ("uncategorized",)),
        interventions=tuple(interventions),
        matched_factors=tuple(matched_factors),
        tissues=tuple(tissues),
        models=tuple(models),
        readouts=tuple(readouts),
        safety_risks=tuple(safety_risks),
        evidence_level=_evidence_level(models),
        evidence_score=_evidence_score(models, readouts, safety_risks, categories),
    )


class ResearchLibrary:
    """SQLite-backed paper library for the literature radar."""

    def __init__(self, db_path: str | Path = DEFAULT_RESEARCH_DB):
        self.db_path = Path(db_path)
        if self.db_path != Path(":memory:"):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(db_path))
        self.connection.row_factory = sqlite3.Row
        initialize_schema(self.connection)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "ResearchLibrary":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def upsert_paper(self, paper: Paper, signals: PaperSignals | None = None) -> StoredPaper:
        return upsert_paper(self.connection, paper, signals=signals)

    def import_papers(self, papers: Iterable[Paper]) -> int:
        count = 0
        for paper in papers:
            self.upsert_paper(paper)
            count += 1
        return count

    def list_papers(self, limit: int | None = 100) -> list[StoredPaper]:
        return list_papers(self.connection, limit=limit)

    def search_papers(self, query: str, limit: int | None = 100) -> list[StoredPaper]:
        return search_papers(self.connection, query=query, limit=limit)

    def papers_for_factor(self, factor_id: str, limit: int | None = 50) -> list[StoredPaper]:
        return papers_for_factor(self.connection, factor_id=factor_id, limit=limit)


def initialize_schema(connection: sqlite3.Connection) -> None:
    """Create paper tables and indexes."""

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS papers (
            paper_id INTEGER PRIMARY KEY AUTOINCREMENT,
            pmid TEXT NOT NULL COLLATE NOCASE,
            title TEXT NOT NULL,
            abstract TEXT NOT NULL DEFAULT '',
            journal TEXT NOT NULL DEFAULT '',
            year INTEGER NOT NULL DEFAULT 0,
            doi TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL DEFAULT '',
            authors_json TEXT NOT NULL DEFAULT '[]',
            signals_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(pmid)
        );

        CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year);
        CREATE INDEX IF NOT EXISTS idx_papers_title ON papers(title);
        CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi);
        """
    )
    connection.commit()


def upsert_paper(
    connection: sqlite3.Connection,
    paper: Paper,
    signals: PaperSignals | None = None,
) -> StoredPaper:
    """Insert or update a paper by PMID."""

    if not paper.pmid:
        raise ValueError("paper.pmid is required")
    signals = signals or analyze_paper_signals(paper)
    payload = _signals_to_dict(signals)
    authors_json = json.dumps(list(paper.authors), ensure_ascii=False)
    signals_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    row = connection.execute("SELECT paper_id FROM papers WHERE lower(pmid) = lower(?)", (paper.pmid,)).fetchone()
    if row is None:
        cursor = connection.execute(
            """
            INSERT INTO papers (pmid, title, abstract, journal, year, doi, url, authors_json, signals_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (paper.pmid, paper.title, paper.abstract, paper.journal, paper.year, paper.doi, paper.url, authors_json, signals_json),
        )
        connection.commit()
        return _get_paper(connection, int(cursor.lastrowid))
    connection.execute(
        """
        UPDATE papers
           SET title = ?,
               abstract = ?,
               journal = ?,
               year = ?,
               doi = ?,
               url = ?,
               authors_json = ?,
               signals_json = ?,
               updated_at = CURRENT_TIMESTAMP
         WHERE paper_id = ?
        """,
        (paper.title, paper.abstract, paper.journal, paper.year, paper.doi, paper.url, authors_json, signals_json, row["paper_id"]),
    )
    connection.commit()
    return _get_paper(connection, int(row["paper_id"]))


def list_papers(connection: sqlite3.Connection, limit: int | None = 100) -> list[StoredPaper]:
    sql = "SELECT * FROM papers ORDER BY year DESC, paper_id DESC"
    params: tuple[int, ...] = ()
    if limit is not None:
        sql += " LIMIT ?"
        params = (_positive_limit(limit),)
    rows = connection.execute(sql, params).fetchall()
    return [_paper_from_row(row) for row in rows]


def search_papers(
    connection: sqlite3.Connection,
    *,
    query: str,
    limit: int | None = 100,
) -> list[StoredPaper]:
    query = (query or "").strip()
    if not query:
        return list_papers(connection, limit=limit)
    tokens = _query_tokens(query)
    if not tokens:
        return list_papers(connection, limit=limit)
    clauses = []
    params_list: list[str | int] = []
    for token in tokens:
        pattern = f"%{token}%"
        clauses.append(
            "(lower(title) LIKE lower(?) OR lower(abstract) LIKE lower(?) OR lower(signals_json) LIKE lower(?))"
        )
        params_list.extend([pattern, pattern, pattern])
    sql = (
        "SELECT * FROM papers "
        f"WHERE {' OR '.join(clauses)} "
        "ORDER BY year DESC, paper_id DESC"
    )
    if limit is not None:
        sql += " LIMIT ?"
        params_list.append(_positive_limit(limit))
    rows = connection.execute(sql, tuple(params_list)).fetchall()
    return [_paper_from_row(row) for row in rows]


def papers_for_factor(
    connection: sqlite3.Connection,
    *,
    factor_id: str,
    limit: int | None = 50,
) -> list[StoredPaper]:
    """Return papers whose extracted signals match a reprogramming factor ID."""

    cleaned = _required_text(factor_id, "factor_id").lower()
    aliases = {
        "osk": ("osk", "oct4 sox2 klf4", "yamanaka"),
        "oskm": ("oskm", "oct4 sox2 klf4 c-myc", "c-myc"),
        "oct4": ("oct4", "pou5f1"),
        "sox2": ("sox2",),
        "klf4": ("klf4",),
        "myc": ("myc", "c-myc"),
        "sirt6": ("sirt6",),
        "tet2": ("tet2",),
        "lin28a": ("lin28a", "lin28"),
        "foxo3": ("foxo3", "foxo3a"),
    }.get(cleaned, (cleaned,))
    clauses = []
    params_list: list[str | int] = []
    for alias in aliases:
        pattern = f"%{alias}%"
        clauses.append(
            "(lower(title) LIKE lower(?) OR lower(abstract) LIKE lower(?) OR lower(signals_json) LIKE lower(?))"
        )
        params_list.extend([pattern, pattern, pattern])
    sql = (
        "SELECT * FROM papers "
        f"WHERE {' OR '.join(clauses)} "
        "ORDER BY year DESC, paper_id DESC"
    )
    if limit is not None:
        sql += " LIMIT ?"
        params_list.append(_positive_limit(limit))
    rows = connection.execute(sql, tuple(params_list)).fetchall()
    return [_paper_from_row(row) for row in rows]


def _get_paper(connection: sqlite3.Connection, paper_id: int) -> StoredPaper:
    row = connection.execute("SELECT * FROM papers WHERE paper_id = ?", (paper_id,)).fetchone()
    if row is None:
        raise ValueError(f"Paper {paper_id} not found")
    return _paper_from_row(row)


def _paper_from_row(row: sqlite3.Row) -> StoredPaper:
    signals_payload = json.loads(row["signals_json"] or "{}")
    if "evidence_score" not in signals_payload or "matched_factors" not in signals_payload:
        signals = analyze_paper_signals(
            Paper(
                pmid=str(row["pmid"]),
                title=str(row["title"]),
                abstract=str(row["abstract"]),
                journal=str(row["journal"]),
                year=int(row["year"]),
                doi=str(row["doi"]),
                url=str(row["url"]),
            )
        )
    else:
        signals = _signals_from_dict(signals_payload)
    return StoredPaper(
        paper_id=int(row["paper_id"]),
        pmid=str(row["pmid"]),
        title=str(row["title"]),
        abstract=str(row["abstract"]),
        journal=str(row["journal"]),
        year=int(row["year"]),
        doi=str(row["doi"]),
        url=str(row["url"]),
        signals=signals,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _signals_to_dict(signals: PaperSignals) -> dict[str, Any]:
    return {
        "categories": list(signals.categories),
        "interventions": list(signals.interventions),
        "matched_factors": list(signals.matched_factors),
        "tissues": list(signals.tissues),
        "models": list(signals.models),
        "readouts": list(signals.readouts),
        "safety_risks": list(signals.safety_risks),
        "evidence_level": signals.evidence_level,
        "evidence_score": signals.evidence_score,
    }


def _signals_from_dict(payload: dict[str, Any]) -> PaperSignals:
    return PaperSignals(
        categories=tuple(payload.get("categories") or ()),
        interventions=tuple(payload.get("interventions") or ()),
        matched_factors=tuple(payload.get("matched_factors") or ()),
        tissues=tuple(payload.get("tissues") or ()),
        models=tuple(payload.get("models") or ()),
        readouts=tuple(payload.get("readouts") or ()),
        safety_risks=tuple(payload.get("safety_risks") or ()),
        evidence_level=str(payload.get("evidence_level") or "unknown"),
        evidence_score=float(payload.get("evidence_score") or 0.0),
    )


def _matches(text: str, patterns: dict[str, tuple[str, ...]]) -> list[str]:
    matches: list[str] = []
    for label, needles in patterns.items():
        if any(needle in text for needle in needles):
            matches.append(label)
    return matches


def _query_tokens(query: str) -> list[str]:
    raw_tokens = [
        token.strip(" \t\r\n,.;:()[]{}\"'")
        for token in query.replace("-", " ").replace("/", " ").split()
    ]
    stopwords = {"and", "or", "the", "with", "for", "from", "into", "aging", "ageing"}
    tokens = []
    for token in raw_tokens:
        lowered = token.lower()
        if len(lowered) < 3 or lowered in stopwords:
            continue
        if lowered not in tokens:
            tokens.append(lowered)
    return tokens


def _evidence_level(models: Iterable[str]) -> str:
    model_set = set(models)
    if "human" in model_set:
        return "human"
    if "non-human primate" in model_set:
        return "primate"
    if "mouse" in model_set:
        return "animal"
    if "organoid" in model_set or "in vitro" in model_set:
        return "preclinical"
    return "unknown"


def _evidence_score(
    models: Iterable[str],
    readouts: Iterable[str],
    safety_risks: Iterable[str],
    categories: Iterable[str],
) -> float:
    model_set = set(models)
    readout_set = set(readouts)
    risk_set = set(safety_risks)
    category_set = set(categories)
    score = 0.18
    if "in vitro" in model_set:
        score += 0.08
    if "organoid" in model_set:
        score += 0.10
    if "mouse" in model_set:
        score += 0.18
    if "non-human primate" in model_set:
        score += 0.24
    if "human" in model_set:
        score += 0.26
    if readout_set:
        score += min(0.22, 0.06 * len(readout_set))
    if "function" in readout_set:
        score += 0.08
    if "partial reprogramming" in category_set:
        score += 0.08
    if risk_set:
        score -= min(0.14, 0.04 * len(risk_set))
    return round(_clamp(score), 3)


def _publication_year(article: ET.Element) -> int:
    for path in (
        ".//Article/Journal/JournalIssue/PubDate/Year",
        ".//PubMedPubDate[@PubStatus='pubmed']/Year",
        ".//PubMedPubDate/Year",
    ):
        value = _text(article.find(path))
        if value.isdigit():
            return int(value)
    return 0


def _article_doi(article: ET.Element) -> str:
    for item in article.findall(".//ArticleId"):
        if item.attrib.get("IdType", "").lower() == "doi":
            return _text(item)
    for item in article.findall(".//ELocationID"):
        if item.attrib.get("EIdType", "").lower() == "doi":
            return _text(item)
    return ""


def _author_name(author: ET.Element) -> str:
    collective = _text(author.find("CollectiveName"))
    if collective:
        return collective
    last = _text(author.find("LastName"))
    fore = _text(author.find("ForeName"))
    return " ".join(part for part in (fore, last) if part)


def _join_text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return " ".join(part.strip() for part in element.itertext() if part.strip())


def _text(element: ET.Element | None) -> str:
    if element is None or element.text is None:
        return ""
    return element.text.strip()


def _required_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required")
    return cleaned


def _positive_limit(value: int) -> int:
    limit = int(value)
    if limit <= 0:
        raise ValueError("limit must be positive")
    return limit


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))
