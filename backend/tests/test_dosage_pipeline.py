"""
Dosage pipeline validation tests — SafeDose
Tests the full call chain:
    extract_drug_inputs()
     └── _extract_dose_frequency_near_term()
    parse_mg_per_day()
    check_dosage()
    compute_safety()
"""

import sys
from pathlib import Path

# ── Bootstrap ──────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

# Clear all LRU caches so updated JSON files are read fresh.
from backend.services import data_loader
data_loader.load_dosage_rules.cache_clear()
data_loader.load_allergy_map.cache_clear()
data_loader.load_interactions.cache_clear()
data_loader.load_alternatives.cache_clear()

from backend.models.schemas import PatientInput
from backend.services.dosage_service import check_dosage, parse_mg_per_day
from backend.services.normalization_service import extract_drug_inputs, normalize_drug_inputs
from backend.services.patient_service import age_category, check_allergies, merge_with_current_medications
from backend.services.safety_service import compute_safety

# ── Helpers ────────────────────────────────────────────────────────────────────

PASS = "PASS"
FAIL = "FAIL"


def run_pipeline(prescription: str, age: int = 30, gender: str = "male"):
    """Run the full dosage pipeline and return a structured result dict."""
    patient = PatientInput(age=age, gender=gender, allergies=[], current_medications=[])
    prescribed = extract_drug_inputs(prescription)
    normalized_drugs, unknowns = merge_with_current_medications(prescribed, [])
    category = age_category(patient.age)
    dosage_issues, dosage_unknowns = check_dosage(normalized_drugs, category)
    unknowns.extend(dosage_unknowns)
    allergy_alerts, allergy_unknowns = check_allergies(patient, normalized_drugs)
    unknowns.extend(allergy_unknowns)
    safety = compute_safety([], dosage_issues, allergy_alerts, unknowns)
    return {
        "drugs": normalized_drugs,
        "dosage_issues": dosage_issues,
        "unknowns": unknowns,
        "safety": safety,
    }


def check(label: str, condition: bool, detail: str = "") -> bool:
    mark = "OK" if condition else "!!"
    print(f"  [{mark}] {label}" + (f" -- {detail}" if detail else ""))
    return condition


# ══════════════════════════════════════════════════════════════════════════════
# Unit tests: parse_mg_per_day()
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("UNIT TESTS: parse_mg_per_day()")
print("=" * 60)

unit_cases = [
    ("500mg", "twice daily",       1000.0),
    ("1500mg", "four times daily", 6000.0),
    ("400mg", "every 6 hours",     1600.0),
    ("250mg", "tid",               750.0),
    ("500mg", "bid",               1000.0),
    ("650mg", "q6h",               2600.0),
    ("1g",    "four times daily",  4000.0),
    ("500mg", "qid",               2000.0),
    ("500mg", "od",                500.0),
    ("500mg", "q12h",              1000.0),
    ("500mg", "once daily",        500.0),
    ("500mg", "daily",             500.0),
    ("500mg", "5 times daily",     2500.0),
    ("500mg", "six times daily",   3000.0),
]

unit_pass = 0
for dosage, freq, expected in unit_cases:
    result = parse_mg_per_day(dosage, freq)
    ok = result == expected
    unit_pass += ok
    check(f"parse_mg_per_day('{dosage}', '{freq}') == {expected}", ok, f"got {result}")

print(f"\n  Unit sub-total: {unit_pass}/{len(unit_cases)} passed")


# ══════════════════════════════════════════════════════════════════════════════
# Integration tests: full pipeline
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("INTEGRATION TESTS: Full Pipeline")
print("=" * 60)

test_cases = [
    # (description, prescription_text, expected_mg_per_day, expected_issue, expected_not_safe)
    ("paracetamol 1500mg four times daily", "prescribe paracetamol 1500mg four times daily", 6000.0, "overdose", True),
    ("paracetamol 500mg twice daily",       "prescribe paracetamol 500mg twice daily",       1000.0, None,       False),
    ("ibuprofen 400mg every 6 hours",       "prescribe ibuprofen 400mg every 6 hours",       1600.0, "overdose", True),
    ("amoxicillin 500mg tid",               "prescribe amoxicillin 500mg tid",               1500.0, None,       False),
    ("clarithromycin 500mg twice daily",    "prescribe clarithromycin 500mg twice daily",    1000.0, None,       False),
    ("paracetamol 650mg q6h",               "prescribe paracetamol 650mg q6h",               2600.0, None,       False),
    ("paracetamol 1g four times daily",     "prescribe paracetamol 1g four times daily",     4000.0, None,       False),
]

integration_pass = 0
integration_total = 0

for desc, prescription, exp_mgday, exp_issue, exp_not_safe in test_cases:
    print(f"\n--- Test: {desc} ---")
    result = run_pipeline(prescription)

    # Find the relevant drug
    drug_obj = result["drugs"][0] if result["drugs"] else None
    issues   = result["dosage_issues"]
    unknowns = result["unknowns"]
    safety   = result["safety"]

    print(f"  drug          : {drug_obj.normalized_name if drug_obj else 'NOT FOUND'}")
    print(f"  dosage_text   : {drug_obj.dosage_text if drug_obj else '-'}")
    print(f"  frequency_text: {drug_obj.frequency_text if drug_obj else '-'}")
    print(f"  mg_per_day    : {drug_obj.mg_per_day if drug_obj else '-'}")
    print(f"  dosage_issue  : {issues[0].issue if issues else 'none'}")
    print(f"  safety        : {safety}")

    t1 = check("Drug extracted",             drug_obj is not None)
    t2 = check("mg_per_day correct",         drug_obj is not None and drug_obj.mg_per_day == exp_mgday,
                                             f"expected {exp_mgday}, got {drug_obj.mg_per_day if drug_obj else None}")
    t3 = check("Dosage issue correct",
               (issues[0].issue == exp_issue if exp_issue else not issues),
               f"expected {exp_issue!r}, got {issues[0].issue if issues else None}")
    t4 = check("Safety correct",
               (safety != 'safe' if exp_not_safe else safety == 'safe'),
               f"got '{safety}'")

    case_pass = all([t1, t2, t3, t4])
    integration_pass += case_pass
    integration_total += 1

# ══════════════════════════════════════════════════════════════════════════════
# Final summary
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"  Unit tests       : {unit_pass}/{len(unit_cases)}")
print(f"  Integration tests: {integration_pass}/{integration_total}")

all_pass = unit_pass == len(unit_cases) and integration_pass == integration_total
print(f"\n  Overall: {'ALL PASS' if all_pass else 'SOME TESTS FAILED'}")
sys.exit(0 if all_pass else 1)
