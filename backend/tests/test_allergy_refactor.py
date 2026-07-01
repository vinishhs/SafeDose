"""
Validation tests for the refactored allergy engine.
Tests 1-4 as specified in the refactoring task.
"""

import json
import sys
from pathlib import Path

# Ensure backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

# Clear lru_cache so the updated allergy_map.json is loaded fresh
from backend.services import data_loader
data_loader.load_allergy_map.cache_clear()

from backend.models.schemas import AllergyAlert, NormalizedDrug, PatientInput, UnknownItem
from backend.services.patient_service import check_allergies


def make_drug(name: str) -> NormalizedDrug:
    return NormalizedDrug(
        original_name=name,
        normalized_name=name.strip().lower(),
        source="input",
    )


def run_test(test_num: int, allergies: list[str], drug_names: list[str],
             expected_alerts: int, expected_unknowns: int, extra_checks=None):
    patient = PatientInput(age=35, allergies=allergies)
    drugs = [make_drug(d) for d in drug_names]

    alerts, unknowns = check_allergies(patient, drugs)

    status = "PASS"
    failures = []

    if len(alerts) != expected_alerts:
        status = "FAIL"
        failures.append(f"  Expected {expected_alerts} alert(s), got {len(alerts)}")
    if len(unknowns) != expected_unknowns:
        status = "FAIL"
        failures.append(f"  Expected {expected_unknowns} unknown(s), got {len(unknowns)}")
    if extra_checks:
        for check_fn, desc in extra_checks:
            if not check_fn(alerts, unknowns):
                status = "FAIL"
                failures.append(f"  Failed extra check: {desc}")

    print(f"\n--- Test {test_num} ---")
    print(f"Allergies : {allergies}")
    print(f"Drugs     : {drug_names}")
    print(f"Alerts    : {[a.model_dump() for a in alerts]}")
    print(f"Unknowns  : {[u.model_dump() for u in unknowns]}")
    print(f"Result    : {status}")
    if failures:
        for f in failures:
            print(f)
    return status == "PASS"


# ── Test 1 ────────────────────────────────────────────────────────────────────
t1 = run_test(
    test_num=1,
    allergies=["nsaid"],
    drug_names=["ibuprofen"],
    expected_alerts=1,
    expected_unknowns=0,
    extra_checks=[
        (lambda a, u: a[0].allergen == "nsaid" and a[0].drug == "ibuprofen",
         "alert has allergen=nsaid and drug=ibuprofen"),
        (lambda a, u: a[0].severity == "high",
         "severity is high"),
        (lambda a, u: "NSAID" in a[0].recommendation,
         "recommendation mentions NSAID"),
        (lambda a, u: a[0].source_id == "allergy_map.json",
         "source_id is allergy_map.json"),
    ],
)

# ── Test 2 ────────────────────────────────────────────────────────────────────
t2 = run_test(
    test_num=2,
    allergies=["penicillin"],
    drug_names=["amoxicillin"],
    expected_alerts=1,
    expected_unknowns=0,
    extra_checks=[
        (lambda a, u: a[0].allergen == "penicillin" and a[0].drug == "amoxicillin",
         "alert has allergen=penicillin and drug=amoxicillin"),
        (lambda a, u: a[0].severity == "high",
         "severity is high"),
        (lambda a, u: a[0].source_id == "allergy_map.json",
         "source_id is allergy_map.json"),
    ],
)

# ── Test 3 ────────────────────────────────────────────────────────────────────
t3 = run_test(
    test_num=3,
    allergies=["shellfish"],
    drug_names=["ibuprofen"],
    expected_alerts=0,
    expected_unknowns=1,
    extra_checks=[
        (lambda a, u: u[0].reason == "Allergy is not present in allergy_map.json.",
         "UnknownItem has correct reason"),
        (lambda a, u: u[0].type == "allergy",
         "UnknownItem type is 'allergy'"),
    ],
)

# ── Test 4 ────────────────────────────────────────────────────────────────────
t4 = run_test(
    test_num=4,
    allergies=["NSAID"],   # uppercase — must still match
    drug_names=["ibuprofen"],
    expected_alerts=1,
    expected_unknowns=0,
    extra_checks=[
        (lambda a, u: a[0].allergen == "nsaid",
         "allergen is normalised to lowercase 'nsaid'"),
    ],
)

# ── Summary ───────────────────────────────────────────────────────────────────
results = {"Test 1": t1, "Test 2": t2, "Test 3": t3, "Test 4": t4}
print("\n==============================")
print("SUMMARY")
print("==============================")
for name, passed in results.items():
    print(f"  {name}: {'PASS' if passed else 'FAIL'}")

all_pass = all(results.values())
print(f"\nOverall: {'ALL PASS ✓' if all_pass else 'SOME TESTS FAILED ✗'}")
sys.exit(0 if all_pass else 1)
