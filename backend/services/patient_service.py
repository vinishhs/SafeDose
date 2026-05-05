from typing import List

from backend.models.schemas import AllergyAlert, DrugInput, NormalizedDrug, PatientInput, UnknownItem
from backend.services.data_loader import load_allergy_map
from backend.services.normalization_service import normalize_drug_inputs


def age_category(age: int) -> str:
    if age < 18:
        return "child"
    if age > 65:
        return "elderly"
    return "adult"


def merge_with_current_medications(
    prescribed: List[DrugInput],
    current_medications: List[str],
) -> tuple[List[NormalizedDrug], List[UnknownItem]]:
    current = [
        DrugInput(name=medication, source="current_medication")
        for medication in current_medications
        if medication and medication.strip()
    ]
    return normalize_drug_inputs([*prescribed, *current])


def check_allergies(patient: PatientInput, drugs: List[NormalizedDrug]) -> tuple[List[AllergyAlert], List[UnknownItem]]:
    allergy_map = load_allergy_map()
    alerts: List[AllergyAlert] = []
    unknowns: List[UnknownItem] = []
    drug_names = {drug.normalized_name for drug in drugs}

    for allergy in patient.allergies:
        allergy_key = allergy.strip().lower()
        if not allergy_key:
            continue

        entry = allergy_map.get(allergy_key)
        if not isinstance(entry, dict):
            unknowns.append(
                UnknownItem(
                    type="allergy",
                    value=allergy,
                    reason="Allergy is not present in allergy_map.json.",
                    source="patient.allergies",
                )
            )
            continue

        severity = entry.get("severity", "unknown")
        for mapped_drug in entry.get("drugs", []):
            normalized_mapped = str(mapped_drug).strip().lower()
            if normalized_mapped not in drug_names:
                continue
            alerts.append(
                AllergyAlert(
                    allergen=allergy_key,
                    drug=normalized_mapped,
                    severity=severity,
                    recommendation=entry.get("recommendation", "UNKNOWN"),
                    source_id=entry.get("source_id", "UNKNOWN"),
                )
            )

    return alerts, unknowns
