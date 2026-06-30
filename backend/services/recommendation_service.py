from typing import Iterable, List, Set

from backend.models.schemas import (
    AllergyAlert,
    AlternativeSuggestion,
    DosageIssue,
    InteractionAlert,
    NormalizedDrug,
    PatientInput,
    UnknownItem,
)
from backend.services.data_loader import load_alternatives, load_interactions


def problematic_drugs(
    interactions: Iterable[InteractionAlert],
    dosage_issues: Iterable[DosageIssue],
    allergy_alerts: Iterable[AllergyAlert],
) -> Set[str]:
    drugs: Set[str] = set()
    for alert in interactions:
        drugs.add(alert.drug_a)
        drugs.add(alert.drug_b)
    for issue in dosage_issues:
        drugs.add(issue.drug)
    for allergy in allergy_alerts:
        drugs.add(allergy.drug)
    return drugs


def suggest_alternatives(
    patient: PatientInput,
    all_drugs: List[NormalizedDrug],
    interactions: List[InteractionAlert],
    dosage_issues: List[DosageIssue],
    allergy_alerts: List[AllergyAlert],
) -> tuple[List[AlternativeSuggestion], List[UnknownItem]]:
    alternatives_data = load_alternatives()
    interaction_db = load_interactions()
    suggestions: List[AlternativeSuggestion] = []
    unknowns: List[UnknownItem] = []
    current_drug_names = {drug.normalized_name for drug in all_drugs}

    for original in sorted(problematic_drugs(interactions, dosage_issues, allergy_alerts)):
        entries = alternatives_data.get(original)
        if entries is None:
            continue

        for entry in entries:
            # Support both plain-string entries and legacy dict entries
            if isinstance(entry, dict):
                candidate = str(entry.get("drug", "")).strip().lower()
                reason = entry.get("reason", "UNKNOWN")
                source_id = entry.get("source_id", "UNKNOWN")
            else:
                candidate = str(entry).strip().lower()
                reason = "UNKNOWN"
                source_id = "UNKNOWN"

            if not candidate:
                continue

            if not is_safe_alternative(candidate, current_drug_names - {original}, interaction_db):
                continue

            suggestions.append(
                AlternativeSuggestion(
                    original_drug=original,
                    suggested_drug=candidate,
                    reason=reason,
                    validation_status="safe",
                    source_id=source_id,
                )
            )

    return _dedupe_suggestions(suggestions), unknowns


def is_safe_alternative(alt: str, all_drugs: Set[str], interaction_db: dict) -> bool:
    for drug in all_drugs:
        key1 = f"{alt}|{drug}"
        key2 = f"{drug}|{alt}"

        if key1 in interaction_db or key2 in interaction_db:
            return False

    return True


def _dedupe_suggestions(suggestions: List[AlternativeSuggestion]) -> List[AlternativeSuggestion]:
    deduped: List[AlternativeSuggestion] = []
    seen = set()
    for suggestion in suggestions:
        key = (suggestion.original_drug, suggestion.suggested_drug)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(suggestion)
    return deduped
