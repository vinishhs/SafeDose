import re
from typing import List, Optional

from backend.models.schemas import DosageIssue, NormalizedDrug, UnknownItem
from backend.services.data_loader import load_dosage_rules


# Canonical frequency-to-multiplier table.
# Entries are matched in insertion order (Python 3.7+ dicts are ordered).
# Longest/most-specific entries appear first to avoid "daily" eating
# "twice daily" etc.
FREQUENCY_MULTIPLIERS: dict[str, float] = {
    "six times daily": 6,
    "five times daily": 5,
    "four times daily": 4,
    "three times daily": 3,
    "thrice daily": 3,
    "twice daily": 2,
    "once daily": 1,
    # Latin / abbreviation forms
    "qid": 4,
    "tid": 3,
    "bid": 2,
    "od": 1,
    # Every-N-hours forms
    "q6h": 4,
    "q8h": 3,
    "q12h": 2,
    "every 6 hours": 4,
    "every 8 hours": 3,
    "every 12 hours": 2,
    # Catch-all
    "daily": 1,
    "every day": 1,
}

# Word-number aliases used when the combined text contains e.g. "4 times daily"
_WORD_NUMBERS: dict[str, int] = {
    "one": 1, "two": 2, "three": 3,
    "four": 4, "five": 5, "six": 6,
}

# Compiled regex — longest keys first to avoid premature partial matches.
_FREQ_REGEX = re.compile(
    r"("
    + "|".join(re.escape(k) for k in FREQUENCY_MULTIPLIERS)
    + r"|[1-6]\s+times?\s+daily"
    r")",
    flags=re.IGNORECASE,
)

# Matches dosage values: supports mg and g (e.g. "1g", "500mg", "1.5g")
_DOSE_REGEX = re.compile(r"(\d+(?:\.\d+)?)\s*(mg|g)\b", flags=re.IGNORECASE)


def _parse_frequency(text: str) -> Optional[float]:
    """Return the times-per-day multiplier for the first frequency token found."""
    m = _FREQ_REGEX.search(text)
    if not m:
        return None
    token = m.group(1).strip().lower()

    # Handle "N times daily" (numeric form like "4 times daily")
    numeric_match = re.match(r"([1-6])\s+times?\s+daily", token)
    if numeric_match:
        return float(numeric_match.group(1))

    return float(FREQUENCY_MULTIPLIERS[token])


def parse_mg_per_day(dosage_text: Optional[str], frequency_text: Optional[str]) -> Optional[float]:
    """Convert dosage_text + frequency_text into a total mg/day figure.

    Supports mg and g units; supports all frequency forms in FREQUENCY_MULTIPLIERS.
    Returns None only when the dosage value itself cannot be parsed.
    """
    if not dosage_text:
        return None

    combined = f"{dosage_text} {frequency_text or ''}".strip()

    dose_match = _DOSE_REGEX.search(combined)
    if not dose_match:
        return None

    dose_mg = float(dose_match.group(1))
    if dose_match.group(2).lower() == "g":
        dose_mg *= 1000

    multiplier = _parse_frequency(combined)
    if multiplier is None:
        # No frequency found — assume once daily as the safe default
        multiplier = 1.0

    return dose_mg * multiplier


def check_dosage(drugs: List[NormalizedDrug], age_category: str) -> tuple[List[DosageIssue], List[UnknownItem]]:
    issues: List[DosageIssue] = []
    unknowns: List[UnknownItem] = []
    rules = load_dosage_rules()

    for drug in drugs:
        # Skip dosage parsing for current medications lacking dosage/frequency info
        if drug.source == "current_medications" and (not drug.dosage_text or not drug.frequency_text):
            drug.mg_per_day = None
            # Do not emit a dosage_parse unknown; continue to next drug for interaction/allergy checks
            continue

        drug_rules = rules.get(drug.normalized_name)
        if not isinstance(drug_rules, dict):
            unknowns.append(
                UnknownItem(
                    type="dosage_rule",
                    value=drug.normalized_name,
                    reason="No dosage rule is present in dosage_rules.json.",
                    source="dosage_rules.json",
                )
            )
            continue

        category_rule = drug_rules.get(age_category)
        if not isinstance(category_rule, dict):
            if age_category == "elderly" and isinstance(drug_rules.get("adult"), dict):
                category_rule = drug_rules["adult"]
                drug.trace["fallback_used"] = True
                drug.trace["rule_source"] = "adult_fallback"
            else:
                unknowns.append(
                    UnknownItem(
                        type="dosage_rule",
                        value=f"{drug.normalized_name}:{age_category}",
                        reason="No dosage rule exists for this age category.",
                        source="dosage_rules.json",
                    )
                )
                continue

        parsed = parse_mg_per_day(drug.dosage_text, drug.frequency_text)
        drug.mg_per_day = parsed
        if parsed is None:
            # Skip dosage‑parse warnings for current‑medication entries lacking dosage/frequency
            if drug.source == "current_medication":
                drug.mg_per_day = None
                continue
            unknowns.append(
                UnknownItem(
                    type="dosage_parse",
                    value=drug.normalized_name,
                    reason="Dosage or frequency could not be parsed into mg/day.",
                    source=drug.source,
                )
            )
            continue

        min_dose = category_rule.get("min")
        max_dose = category_rule.get("max")
        source_id = category_rule.get("source_id", "dosage_rules.json")
        overdose_severity = category_rule.get("overdose_severity", "high")
        underdose_severity = category_rule.get("underdose_severity", "moderate")

        if min_dose is None or max_dose is None:
            unknowns.append(
                UnknownItem(
                    type="dosage_range",
                    value=f"{drug.normalized_name}:{age_category}",
                    reason="Dosage rule is missing min or max.",
                    source="dosage_rules.json",
                )
            )
            continue

        if parsed < float(min_dose):
            issues.append(
                DosageIssue(
                    drug=drug.normalized_name,
                    severity=underdose_severity,
                    issue="underdose",
                    parsed_mg_per_day=parsed,
                    min_mg_per_day=float(min_dose),
                    max_mg_per_day=float(max_dose),
                    recommendation="Dose may be below the recommended minimum. Review and adjust.",
                    source_id=source_id,
                )
            )
        elif parsed > float(max_dose):
            issues.append(
                DosageIssue(
                    drug=drug.normalized_name,
                    severity=overdose_severity,
                    issue="overdose",
                    parsed_mg_per_day=parsed,
                    min_mg_per_day=float(min_dose),
                    max_mg_per_day=float(max_dose),
                    recommendation="Maximum daily dose exceeded. Reduce dose immediately.",
                    source_id=source_id,
                )
            )

    return issues, unknowns
