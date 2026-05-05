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
from backend.services.data_loader import load_alternatives
from backend.services.interaction_service import interaction_entry
from backend.services.patient_service import check_allergies


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
    suggestions: List[AlternativeSuggestion] = []
    unknowns: List[UnknownItem] = []
    current_drug_names = {drug.normalized_name for drug in all_drugs}

    for original in sorted(problematic_drugs(interactions, dosage_issues, allergy_alerts)):
        entries = alternatives_data.get(original)
        if entries is None:
            unknowns.append(
                UnknownItem(
                    type="alternative",
                    value=original,
                    reason="No alternatives are present in alternatives.json.",
                    source="alternatives.json",
                )
            )
            continue

        for entry in entries:
            candidate = str(entry.get("drug", "")).strip().lower()
            if not candidate:
                unknowns.append(
                    UnknownItem(
                        type="alternative",
                        value=original,
                        reason="Alternative entry is missing a drug name.",
                        source="alternatives.json",
                    )
                )
                continue

            validation_unknowns = _validate_alternative(candidate, original, current_drug_names)
            if validation_unknowns:
                unknowns.extend(validation_unknowns)
                continue

            candidate_drugs = [
                drug for drug in all_drugs if drug.normalized_name != original
            ] + [
                NormalizedDrug(
                    original_name=candidate,
                    normalized_name=candidate,
                    source="alternative_validation",
                )
            ]
            allergy_alerts_for_candidate, allergy_unknowns = check_allergies(patient, candidate_drugs)
            if allergy_unknowns:
                unknowns.extend(allergy_unknowns)
                continue
            if allergy_alerts_for_candidate:
                continue

            suggestions.append(
                AlternativeSuggestion(
                    original_drug=original,
                    suggested_drug=candidate,
                    reason=entry.get("reason", "UNKNOWN"),
                    validation_status="safe",
                    source_id=entry.get("source_id", "UNKNOWN"),
                )
            )

    return _dedupe_suggestions(suggestions), unknowns


def _validate_alternative(candidate: str, original: str, current_drug_names: Set[str]) -> List[UnknownItem]:
    unknowns: List[UnknownItem] = []
    for existing in sorted(current_drug_names):
        if existing == original:
            continue
        entry = interaction_entry(candidate, existing)
        if entry is not None:
            return [
                UnknownItem(
                    type="alternative_rejected",
                    value=f"{original}->{candidate}",
                    reason=f"Candidate has dataset interaction with {existing}.",
                    source="interactions.json",
                )
            ]

        unknowns.append(
            UnknownItem(
                type="alternative_validation",
                value=f"{candidate}|{existing}",
                reason="No interaction rule is present to prove this alternative safe.",
                source="interactions.json",
            )
        )

    return unknowns


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
