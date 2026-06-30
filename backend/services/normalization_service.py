import re
from difflib import get_close_matches
from typing import Dict, Iterable, List, Optional, Set

try:
    from rapidfuzz import fuzz, process
except ImportError:  # Keeps the service importable until dependencies are installed.
    fuzz = None
    process = None

from backend.models.schemas import DrugInput, NormalizedDrug, UnknownItem
from backend.services.data_loader import (
    load_allergy_map,
    load_alternatives,
    load_dosage_rules,
    load_interactions,
)


UNKNOWN = "UNKNOWN"
FUZZY_THRESHOLD = 82
PARTIAL_THRESHOLD = 88
ALIASES = {
    "atorva": "atorvastatin",
    "clarithro": "clarithromycin",
}


def _clean_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s-]", " ", name or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


def _dataset_drugs() -> Set[str]:
    drugs: Set[str] = set()

    dosage_rules = load_dosage_rules()
    drugs.update(key for key in dosage_rules if not key.startswith("_"))

    alternatives = load_alternatives()
    drugs.update(alternatives.keys())
    for entries in alternatives.values():
        for entry in entries:
            if isinstance(entry, dict) and entry.get("drug"):
                drugs.add(str(entry["drug"]).lower())

    for pair in load_interactions():
        drugs.update(pair.split("|"))

    for allergy in load_allergy_map().values():
        if isinstance(allergy, dict):
            drugs.update(str(drug).lower() for drug in allergy.get("drugs", []))

    return {_clean_name(drug) for drug in drugs if _clean_name(drug)}


def _brand_to_generic() -> Dict[str, str]:
    mapping = load_dosage_rules().get("_brand_to_generic", {})
    if not isinstance(mapping, dict):
        mapping = {}
    brand_map = {_clean_name(brand): _clean_name(generic) for brand, generic in mapping.items()}
    brand_map.update(ALIASES)
    return brand_map


def normalize_drug(name: str) -> str:
    cleaned = _clean_name(name)
    if not cleaned:
        return UNKNOWN

    brand_map = _brand_to_generic()
    if cleaned in brand_map:
        return brand_map[cleaned]

    known_drugs = _dataset_drugs()
    if cleaned in known_drugs:
        return cleaned

    if process is not None and fuzz is not None:
        match = process.extractOne(cleaned, known_drugs, scorer=fuzz.WRatio)
        if match and match[1] >= FUZZY_THRESHOLD:
            return str(match[0])
        partial_match = process.extractOne(cleaned, known_drugs, scorer=fuzz.partial_ratio)
        if partial_match and partial_match[1] >= PARTIAL_THRESHOLD:
            return str(partial_match[0])
    else:
        matches = get_close_matches(cleaned, known_drugs, n=1, cutoff=FUZZY_THRESHOLD / 100)
        if matches:
            return matches[0]
        prefix_matches = [drug for drug in known_drugs if drug.startswith(cleaned) and len(cleaned) >= 5]
        if len(prefix_matches) == 1:
            return prefix_matches[0]

    return UNKNOWN


def known_terms() -> Dict[str, str]:
    terms = {drug: drug for drug in _dataset_drugs()}
    terms.update(_brand_to_generic())
    return terms


def extract_drug_inputs(text: str) -> List[DrugInput]:
    if not text:
        return []

    found: List[DrugInput] = []
    seen: Set[str] = set()
    terms = known_terms()
    lowered = text.lower()

    for term, generic in sorted(terms.items(), key=lambda item: len(item[0]), reverse=True):
        if not re.search(rf"\b{re.escape(term)}\b", lowered):
            continue
        if generic in seen:
            continue
        dosage, frequency = _extract_dose_frequency_near_term(lowered, term)
        found.append(
            DrugInput(
                name=term,
                dosage=dosage,
                frequency=frequency,
                source="prescription_text",
            )
        )
        seen.add(generic)

    if not found:
        found.extend(_fallback_extract_drug_inputs(lowered, terms, seen))

    return found


def normalize_drug_inputs(drugs: Iterable[DrugInput]) -> tuple[List[NormalizedDrug], List[UnknownItem]]:
    normalized: List[NormalizedDrug] = []
    unknowns: List[UnknownItem] = []

    for drug in drugs:
        normalized_name = normalize_drug(drug.name)
        if normalized_name == UNKNOWN:
            unknowns.append(
                UnknownItem(
                    type="drug",
                    value=drug.name,
                    reason="Drug is not present in the allowed datasets.",
                    source=drug.source,
                )
            )
            continue
        normalized.append(
            NormalizedDrug(
                original_name=drug.name,
                normalized_name=normalized_name,
                dosage_text=drug.dosage,
                frequency_text=drug.frequency,
                source=drug.source,
                trace={"normalization": "brand/exact/fuzzy dataset match"},
            )
        )

    return normalized, unknowns


def _fallback_extract_drug_inputs(text: str, terms: Dict[str, str], seen: Set[str]) -> List[DrugInput]:
    found: List[DrugInput] = []
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9-]+", text)

    for token in tokens:
        normalized = normalize_drug(token)
        if normalized == UNKNOWN or normalized in seen:
            continue
        term = next((key for key, value in terms.items() if value == normalized), token)
        dosage, frequency = _extract_dose_frequency_near_term(text, token)
        found.append(
            DrugInput(
                name=term,
                dosage=dosage,
                frequency=frequency,
                source="prescription_text_fallback",
            )
        )
        seen.add(normalized)

    return found


def _extract_dose_frequency_near_term(text: str, term: str) -> tuple[Optional[str], Optional[str]]:
    match = re.search(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE)
    if not match:
        return None, None

    window = text[match.end() : match.end() + 70]
    dosage_match = re.search(r"(\d+(?:\.\d+)?)\s*mg", window, flags=re.IGNORECASE)
    frequency_match = re.search(
        r"(once daily|twice daily|three times daily|thrice daily|daily|bid|tid|qid)",
        window,
        flags=re.IGNORECASE,
    )

    dosage = f"{dosage_match.group(1)}mg" if dosage_match else None
    frequency = frequency_match.group(1).lower() if frequency_match else None
    return dosage, frequency
