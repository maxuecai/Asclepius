"""Molecular structure utilities with optional RDKit acceleration."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Iterable


try:  # pragma: no cover - depends on optional local chemistry stack.
    from rdkit import Chem
    from rdkit.Chem import Crippen, Descriptors, Lipinski, QED, rdMolDescriptors

    HAS_RDKIT = True
except Exception:  # pragma: no cover - exercised when RDKit is unavailable.
    Chem = None
    Crippen = Descriptors = Lipinski = QED = rdMolDescriptors = None
    HAS_RDKIT = False


ATOM_WEIGHTS = {
    "C": 12.011,
    "N": 14.007,
    "O": 15.999,
    "S": 32.06,
    "P": 30.974,
    "F": 18.998,
    "Cl": 35.45,
    "Br": 79.904,
    "I": 126.904,
}
ATOM_RE = re.compile(r"Cl|Br|[CNOSPFIcnosp]")


@dataclass(frozen=True)
class MoleculeProperties:
    """Computed molecular descriptors for scoring and display."""

    smiles: str
    valid: bool
    engine: str
    formula: str
    heavy_atom_count: int
    hetero_atom_count: int
    molecular_weight: float
    logp: float
    tpsa: float
    hbd: int
    hba: int
    rotatable_bonds: int
    aromatic_rings: int
    qed: float
    lipinski_violations: int
    pains_alerts: tuple[str, ...]
    brenk_alerts: tuple[str, ...]
    synthetic_accessibility: float
    oral_likeness: float
    solubility_class: str
    bbb_permeability: str
    cyp_risk: str
    herg_risk: str
    hepatotoxicity_risk: str
    lead_likeness: float


def analyze_smiles(smiles: str) -> MoleculeProperties:
    """Analyze a SMILES string using RDKit when available, otherwise fallback rules."""

    smiles = smiles.strip()
    if not smiles:
        raise ValueError("SMILES 不能为空")
    if HAS_RDKIT:
        return _analyze_with_rdkit(smiles)
    return _analyze_with_fallback(smiles)


def molecular_fingerprint(smiles: str) -> frozenset[str] | object:
    """Return an RDKit Morgan fingerprint or a fallback token fingerprint."""

    if HAS_RDKIT:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError(f"无法解析 SMILES: {smiles}")
        return rdMolDescriptors.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
    return frozenset(_ngrams(_canonicalish(smiles), 2) | _ngrams(_canonicalish(smiles), 3))


def tanimoto(fp_a: frozenset[str] | object, fp_b: frozenset[str] | object) -> float:
    """Compute Tanimoto similarity for RDKit or fallback fingerprints."""

    if HAS_RDKIT:
        from rdkit import DataStructs

        return float(DataStructs.TanimotoSimilarity(fp_a, fp_b))
    set_a = set(fp_a)
    set_b = set(fp_b)
    if not set_a and not set_b:
        return 1.0
    return len(set_a & set_b) / len(set_a | set_b)


def structure_svg(smiles: str, width: int = 320, height: int = 220) -> str:
    """Render a molecule as SVG when RDKit exists; fallback to a labeled placeholder."""

    if HAS_RDKIT:
        from rdkit.Chem import Draw

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError(f"无法解析 SMILES: {smiles}")
        return Draw.MolsToGridImage([mol], molsPerRow=1, subImgSize=(width, height), useSVG=True)
    escaped = smiles.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}'>"
        "<rect width='100%' height='100%' rx='12' fill='#f6f8f7' stroke='#d8e1e6'/>"
        "<text x='18' y='42' font-family='Helvetica' font-size='18' font-weight='700' fill='#192025'>SMILES</text>"
        f"<text x='18' y='78' font-family='Menlo' font-size='13' fill='#30404a'>{escaped}</text>"
        "<text x='18' y='130' font-family='Helvetica' font-size='12' fill='#63707a'>未检测到 RDKit，当前显示结构文本占位。</text>"
        "</svg>"
    )


def _analyze_with_rdkit(smiles: str) -> MoleculeProperties:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return _invalid_properties(smiles, "rdkit")
    molecular_weight = Descriptors.MolWt(mol)
    formula = rdMolDescriptors.CalcMolFormula(mol)
    heavy_atom_count = mol.GetNumHeavyAtoms()
    hetero_atom_count = sum(1 for atom in mol.GetAtoms() if atom.GetAtomicNum() not in (1, 6))
    logp = Crippen.MolLogP(mol)
    tpsa = rdMolDescriptors.CalcTPSA(mol)
    hbd = Lipinski.NumHDonors(mol)
    hba = Lipinski.NumHAcceptors(mol)
    rotatable_bonds = Lipinski.NumRotatableBonds(mol)
    aromatic_rings = rdMolDescriptors.CalcNumAromaticRings(mol)
    qed = float(QED.qed(mol))
    violations = _lipinski_violations(molecular_weight, logp, hbd, hba)
    pains = _fallback_pains_alerts(smiles)
    brenk = _fallback_brenk_alerts(smiles)
    sa = _synthetic_accessibility(smiles, molecular_weight, aromatic_rings, rotatable_bonds)
    oral = _oral_likeness(molecular_weight, logp, tpsa, hbd, hba, violations, pains, brenk)
    solubility = _solubility_class(logp, molecular_weight)
    bbb = _bbb_permeability(logp, tpsa, hbd)
    cyp = _cyp_risk(logp, aromatic_rings, molecular_weight)
    herg = _herg_risk(logp, aromatic_rings, molecular_weight)
    liver = _hepatotoxicity_risk(logp, brenk, pains)
    lead = _lead_likeness(molecular_weight, logp, rotatable_bonds, violations, pains)
    return MoleculeProperties(
        smiles=Chem.MolToSmiles(mol),
        valid=True,
        engine="RDKit",
        formula=formula,
        heavy_atom_count=heavy_atom_count,
        hetero_atom_count=hetero_atom_count,
        molecular_weight=round(molecular_weight, 3),
        logp=round(logp, 3),
        tpsa=round(tpsa, 3),
        hbd=hbd,
        hba=hba,
        rotatable_bonds=rotatable_bonds,
        aromatic_rings=aromatic_rings,
        qed=round(qed, 3),
        lipinski_violations=violations,
        pains_alerts=tuple(pains),
        brenk_alerts=tuple(brenk),
        synthetic_accessibility=round(sa, 3),
        oral_likeness=round(oral, 3),
        solubility_class=solubility,
        bbb_permeability=bbb,
        cyp_risk=cyp,
        herg_risk=herg,
        hepatotoxicity_risk=liver,
        lead_likeness=round(lead, 3),
    )


def _analyze_with_fallback(smiles: str) -> MoleculeProperties:
    atoms = _atoms(smiles)
    if not atoms:
        return _invalid_properties(smiles, "fallback")
    molecular_weight = sum(ATOM_WEIGHTS.get(atom.capitalize(), 12.011) for atom in atoms)
    hetero = sum(1 for atom in atoms if atom.capitalize() in {"N", "O", "S", "P"})
    halogens = sum(1 for atom in atoms if atom.capitalize() in {"F", "Cl", "Br", "I"})
    carbons = sum(1 for atom in atoms if atom.upper() == "C")
    hbd = len(re.findall(r"\[?NH|OH|nH", smiles))
    hba = hetero + smiles.count("=")
    aromatic_rings = max(0, len(re.findall(r"[cn]", smiles)) // 5)
    ring_markers = len(set(re.findall(r"\d", smiles)))
    rotatable_bonds = max(0, smiles.count("-") + smiles.count("CC") - ring_markers)
    logp = 0.12 * carbons + 0.28 * halogens - 0.28 * hetero - 0.7
    tpsa = 12.0 * hba + 8.0 * hbd + 4.0 * hetero
    violations = _lipinski_violations(molecular_weight, logp, hbd, hba)
    pains = _fallback_pains_alerts(smiles)
    brenk = _fallback_brenk_alerts(smiles)
    qed = _qed_like(molecular_weight, logp, tpsa, hbd, hba, rotatable_bonds, violations, pains)
    sa = _synthetic_accessibility(smiles, molecular_weight, aromatic_rings, rotatable_bonds)
    oral = _oral_likeness(molecular_weight, logp, tpsa, hbd, hba, violations, pains, brenk)
    solubility = _solubility_class(logp, molecular_weight)
    bbb = _bbb_permeability(logp, tpsa, hbd)
    cyp = _cyp_risk(logp, aromatic_rings, molecular_weight)
    herg = _herg_risk(logp, aromatic_rings, molecular_weight)
    liver = _hepatotoxicity_risk(logp, brenk, pains)
    lead = _lead_likeness(molecular_weight, logp, rotatable_bonds, violations, pains)
    return MoleculeProperties(
        smiles=smiles,
        valid=True,
        engine="轻量 SMILES 规则",
        formula=_formula_from_atoms(atoms),
        heavy_atom_count=len(atoms),
        hetero_atom_count=hetero,
        molecular_weight=round(molecular_weight, 3),
        logp=round(logp, 3),
        tpsa=round(tpsa, 3),
        hbd=hbd,
        hba=hba,
        rotatable_bonds=rotatable_bonds,
        aromatic_rings=aromatic_rings,
        qed=round(qed, 3),
        lipinski_violations=violations,
        pains_alerts=tuple(pains),
        brenk_alerts=tuple(brenk),
        synthetic_accessibility=round(sa, 3),
        oral_likeness=round(oral, 3),
        solubility_class=solubility,
        bbb_permeability=bbb,
        cyp_risk=cyp,
        herg_risk=herg,
        hepatotoxicity_risk=liver,
        lead_likeness=round(lead, 3),
    )


def _invalid_properties(smiles: str, engine: str) -> MoleculeProperties:
    return MoleculeProperties(
        smiles=smiles,
        valid=False,
        engine=engine,
        formula="",
        heavy_atom_count=0,
        hetero_atom_count=0,
        molecular_weight=0.0,
        logp=0.0,
        tpsa=0.0,
        hbd=0,
        hba=0,
        rotatable_bonds=0,
        aromatic_rings=0,
        qed=0.0,
        lipinski_violations=4,
        pains_alerts=("无法解析结构",),
        brenk_alerts=(),
        synthetic_accessibility=0.0,
        oral_likeness=0.0,
        solubility_class="未知",
        bbb_permeability="未知",
        cyp_risk="未知",
        herg_risk="未知",
        hepatotoxicity_risk="未知",
        lead_likeness=0.0,
    )


def _atoms(smiles: str) -> list[str]:
    return [match.group(0).capitalize() for match in ATOM_RE.finditer(smiles)]


def _formula_from_atoms(atoms: list[str]) -> str:
    counts: dict[str, int] = {}
    for atom in atoms:
        counts[atom] = counts.get(atom, 0) + 1
    ordered = ["C", "H", "N", "O", "S", "P", "F", "Cl", "Br", "I"]
    parts = []
    for atom in ordered:
        if atom in counts:
            count = counts.pop(atom)
            parts.append(atom if count == 1 else f"{atom}{count}")
    for atom in sorted(counts):
        count = counts[atom]
        parts.append(atom if count == 1 else f"{atom}{count}")
    return "".join(parts)


def _canonicalish(smiles: str) -> str:
    return re.sub(r"\s+", "", smiles)


def _ngrams(text: str, size: int) -> set[str]:
    if len(text) < size:
        return {text}
    return {text[index : index + size] for index in range(len(text) - size + 1)}


def _lipinski_violations(molecular_weight: float, logp: float, hbd: int, hba: int) -> int:
    return sum(
        [
            molecular_weight > 500,
            logp > 5,
            hbd > 5,
            hba > 10,
        ]
    )


def _fallback_pains_alerts(smiles: str) -> list[str]:
    alerts = []
    if re.search(r"O=O|N=N|N#N", smiles):
        alerts.append("反应性/氧化还原警报")
    if len(re.findall(r"c", smiles)) >= 12 and re.search(r"N|O", smiles):
        alerts.append("多芳环富杂原子警报")
    if re.search(r"\[?S\]?=\[?S\]?|N\(=O\)=O", smiles):
        alerts.append("潜在非特异性结构警报")
    return alerts


def _fallback_brenk_alerts(smiles: str) -> list[str]:
    alerts = []
    if "Br" in smiles or "I" in smiles:
        alerts.append("重卤素警报")
    if smiles.count("=") >= 5:
        alerts.append("高不饱和度警报")
    if len(smiles) > 120:
        alerts.append("结构复杂度偏高")
    return alerts


def _qed_like(
    molecular_weight: float,
    logp: float,
    tpsa: float,
    hbd: int,
    hba: int,
    rotatable_bonds: int,
    violations: int,
    pains: Iterable[str],
) -> float:
    score = 1.0
    score -= min(abs(molecular_weight - 350) / 500, 0.35)
    score -= min(abs(logp - 2.5) / 8, 0.25)
    score -= 0.10 if tpsa > 140 else 0.0
    score -= 0.04 * max(0, hbd - 3)
    score -= 0.03 * max(0, hba - 8)
    score -= 0.025 * max(0, rotatable_bonds - 7)
    score -= 0.12 * violations
    score -= 0.10 * len(tuple(pains))
    return _clamp(score)


def _synthetic_accessibility(
    smiles: str,
    molecular_weight: float,
    aromatic_rings: int,
    rotatable_bonds: int,
) -> float:
    complexity = len(smiles) / 120 + aromatic_rings * 0.08 + rotatable_bonds * 0.015
    size_penalty = max(0.0, molecular_weight - 450) / 500
    return _clamp(0.92 - complexity - size_penalty)


def _oral_likeness(
    molecular_weight: float,
    logp: float,
    tpsa: float,
    hbd: int,
    hba: int,
    violations: int,
    pains: Iterable[str],
    brenk: Iterable[str],
) -> float:
    score = 1.0 - 0.16 * violations
    if molecular_weight < 150:
        score -= 0.08
    if not -1 <= logp <= 5:
        score -= 0.12
    if tpsa > 140:
        score -= 0.12
    if hbd > 4 or hba > 9:
        score -= 0.08
    score -= 0.08 * len(tuple(pains))
    score -= 0.05 * len(tuple(brenk))
    return _clamp(score)


def _solubility_class(logp: float, molecular_weight: float) -> str:
    if logp <= 2.5 and molecular_weight <= 450:
        return "较好"
    if logp <= 4.5 and molecular_weight <= 600:
        return "中等"
    return "偏低"


def _bbb_permeability(logp: float, tpsa: float, hbd: int) -> str:
    if 1.0 <= logp <= 4.0 and tpsa <= 90 and hbd <= 2:
        return "可能较高"
    if tpsa <= 120 and hbd <= 4:
        return "中等"
    return "可能较低"


def _cyp_risk(logp: float, aromatic_rings: int, molecular_weight: float) -> str:
    if logp > 4.0 and aromatic_rings >= 2:
        return "高"
    if logp > 3.0 or molecular_weight > 450:
        return "中"
    return "低"


def _herg_risk(logp: float, aromatic_rings: int, molecular_weight: float) -> str:
    if logp > 4.0 and aromatic_rings >= 2 and molecular_weight > 350:
        return "高"
    if logp > 3.0 and molecular_weight > 300:
        return "中"
    return "低"


def _hepatotoxicity_risk(logp: float, brenk: Iterable[str], pains: Iterable[str]) -> str:
    burden = len(tuple(brenk)) + len(tuple(pains))
    if logp > 4.5 or burden >= 2:
        return "高"
    if logp > 3.0 or burden == 1:
        return "中"
    return "低"


def _lead_likeness(
    molecular_weight: float,
    logp: float,
    rotatable_bonds: int,
    violations: int,
    pains: Iterable[str],
) -> float:
    score = 1.0
    if not 150 <= molecular_weight <= 450:
        score -= 0.18
    if not -1 <= logp <= 4:
        score -= 0.16
    if rotatable_bonds > 8:
        score -= 0.08
    score -= 0.14 * violations
    score -= 0.12 * len(tuple(pains))
    return _clamp(score)


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    if math.isnan(value):
        return lower
    return max(lower, min(upper, value))
