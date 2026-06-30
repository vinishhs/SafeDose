import re
from typing import List, Optional

from backend.models.schemas import DosageIssue, NormalizedDrug, UnknownItem
from backend.services.data_loader import load_dosage_rules


FREQUENCY_MULTIPLIERS = {
    "once daily": 1,
    "daily": 1,
    "twice daily": 2,
    "bid": 2,
    "three times daily": 3,
    "thrice daily": 3,
    "tid": 3,
    "qid": 4,
}


def parse_mg_per_day(dosage_text: Optional[str], frequency_text: Optional[str]) -> Optional[float]:
    if not dosage_text:
        return None

    combined_text = f"{dosage_text or ''} {frequency_text or ''}".strip()
    dosage_match = re.search(r"(\d+(?:\.\d+)?)\s*mg", combined_text, flags=re.IGNORECASE)
    if not dosage_match:
        return None

    dose_mg = float(dosage_match.group(1))
    frequency_match = re.search(
        r"(once daily|twice daily|three times daily|thrice daily|daily|bid|tid|qid)",
        combined_text,
        flags=re.IGNORECASE,
    )
    frequency = frequency_match.group(1).strip().lower() if frequency_match else "once daily"
    multiplier = FREQUENCY_MULTIPLIERS.get(frequency)
    if multiplier is None:
        return None

    return dose_mg * multiplier


def check_dosage(drugs: List[NormalizedDrug], age_category: str) -> tuple[List[DosageIssue], List[UnknownItem]]:
    issues: List[DosageIssue] = []
    unknowns: List[UnknownItem] = []
    rules = load_dosage_rules()

    for drug in drugs:
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
        source_id = category_rule.get("source_id", "UNKNOWN")

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
                    severity=category_rule.get("underdose_severity", "unknown"),
                    issue="underdose",
                    parsed_mg_per_day=parsed,
                    min_mg_per_day=float(min_dose),
                    max_mg_per_day=float(max_dose),
                    recommendation="Review dose against dataset minimum.",
                    source_id=source_id,
                )
            )
        elif parsed > float(max_dose):
            issues.append(
                DosageIssue(
                    drug=drug.normalized_name,
                    severity=category_rule.get("overdose_severity", "unknown"),
                    issue="overdose",
                    parsed_mg_per_day=parsed,
                    min_mg_per_day=float(min_dose),
                    max_mg_per_day=float(max_dose),
                    recommendation="Review dose against dataset maximum.",
                    source_id=source_id,
                )
            )

    return issues, unknowns
