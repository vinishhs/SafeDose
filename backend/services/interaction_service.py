from itertools import combinations
from typing import List, Optional

from backend.models.schemas import InteractionAlert, NormalizedDrug, UnknownItem
from backend.services.data_loader import load_interactions


def _pair_key(drug_a: str, drug_b: str) -> str:
    return "|".join(sorted([drug_a, drug_b]))


def interaction_entry(drug_a: str, drug_b: str) -> Optional[dict]:
    interactions = load_interactions()
    direct = f"{drug_a}|{drug_b}"
    reverse = f"{drug_b}|{drug_a}"
    sorted_key = _pair_key(drug_a, drug_b)
    return interactions.get(direct) or interactions.get(reverse) or interactions.get(sorted_key)


def check_interactions(drugs: List[NormalizedDrug]) -> tuple[List[InteractionAlert], List[UnknownItem]]:
    alerts: List[InteractionAlert] = []
    unknowns: List[UnknownItem] = []
    seen_pairs = set()

    unique_names = []
    for drug in drugs:
        if drug.normalized_name not in unique_names:
            unique_names.append(drug.normalized_name)

    for drug_a, drug_b in combinations(unique_names, 2):
        pair_key = _pair_key(drug_a, drug_b)
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        entry = interaction_entry(drug_a, drug_b)
        if entry is None:
            # No documented interaction; do not generate an UnknownItem.
            continue

        severity = entry.get("severity", "unknown")
        if severity == "unknown":
            unknowns.append(
                UnknownItem(
                    type="interaction_severity",
                    value=pair_key,
                    reason="Interaction entry does not include explicit severity.",
                    source="interactions.json",
                )
            )

        alerts.append(
            InteractionAlert(
                drug_a=drug_a,
                drug_b=drug_b,
                severity=severity,
                mechanism=entry.get("mechanism", "UNKNOWN"),
                effect=entry.get("effect", "UNKNOWN"),
                recommendation=entry.get("recommendation", "UNKNOWN"),
                source_id=entry.get("source_id", "UNKNOWN"),
            )
        )

    return alerts, unknowns
