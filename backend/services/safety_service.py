from typing import List

from backend.models.schemas import AllergyAlert, DosageIssue, InteractionAlert, SafetyStatus, UnknownItem


def compute_safety(
    interactions: List[InteractionAlert],
    dosage_issues: List[DosageIssue],
    allergy_alerts: List[AllergyAlert],
    unknowns: List[UnknownItem],
) -> SafetyStatus:
    if any(alert.severity == "high" for alert in interactions):
        return "unsafe"

    has_moderate_interaction = any(alert.severity == "moderate" for alert in interactions)
    if has_moderate_interaction or dosage_issues or allergy_alerts:
        return "caution"

    return "safe"
