#!/usr/bin/env python3
"""
SafeDose Regression Test Runner
================================
Usage:
    python scripts/run_regression_tests.py
    python scripts/run_regression_tests.py --filter "Paracetamol"
    python scripts/run_regression_tests.py --fail-fast

Automatically fixes sys.path so that the 'backend' package is importable
regardless of the working directory the script is invoked from.
"""

import argparse
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Optional


# ── Path bootstrap ─────────────────────────────────────────────────────────────
# Ensure the project root (parent of 'backend/') is on sys.path
# so that `from backend.main import app` works correctly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Dynamically discover all test case JSON files in the tests directory
TESTS_DIR = PROJECT_ROOT / "tests"
TEST_CASES_PATHS = sorted(TESTS_DIR.glob("*.json"))
# Load and combine all test cases from discovered JSON files with validation
combined_test_cases: list[dict] = []
# Mapping filename -> number of tests loaded
test_file_stats: dict[str, int] = {}
# List of (path, error_message) for files that could not be processed
invalid_files: list[tuple[Path, str]] = []
for path in TEST_CASES_PATHS:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            cases = json.load(fh)
    except Exception as exc:
        invalid_files.append((path, f"Invalid JSON: {exc}"))
        continue
    if not isinstance(cases, list):
        invalid_files.append((path, f"Root element is not a list (found {type(cases).__name__})"))
        continue
    if not all(isinstance(item, dict) for item in cases):
        invalid_files.append((path, "Not all items are dict objects"))
        continue
    test_file_stats[path.name] = len(cases)
    combined_test_cases.extend(cases)
# Report any malformed files but continue execution
if invalid_files:
    print("\nInvalid Test Files:")
    print("-" * 30)
    for p, reason in invalid_files:
        print(f"✗ {p.name}: {reason}")
    print("-" * 30)

# ── FastAPI test client ────────────────────────────────────────────────────────
try:
    from fastapi.testclient import TestClient
    from backend.main import app  # noqa: E402
except ImportError as exc:
    print(f"\n[ERROR] Failed to import required modules: {exc}")
    print("Make sure you are running from the project root and the venv is active.")
    sys.exit(1)

client = TestClient(app)

# ── ANSI colour helpers ────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
DIM    = "\033[2m"

def green(s):  return f"{GREEN}{s}{RESET}"
def red(s):    return f"{RED}{s}{RESET}"
def yellow(s): return f"{YELLOW}{s}{RESET}"
def cyan(s):   return f"{CYAN}{s}{RESET}"
def bold(s):   return f"{BOLD}{s}{RESET}"
def dim(s):    return f"{DIM}{s}{RESET}"

SEP  = "=" * 70
THIN = "-" * 70


# ── Validation helpers ─────────────────────────────────────────────────────────

def _validate(result: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    """
    Compare actual API response fields against the expected block.
    Returns a list of failure reasons (empty list = PASS).
    """
    failures: list[str] = []

    field_map = {
        "safety":               lambda r: r.get("safety"),
        "interaction_count":    lambda r: len(r.get("interactions", [])),
        "dosage_issue_count":   lambda r: len(r.get("dosage_issues", [])),
        "allergy_count":        lambda r: len(r.get("allergy_alerts", [])),
        "alternative_count":    lambda r: len(r.get("alternatives", [])),
        "unknown_count":        lambda r: len(r.get("unknowns", [])),
    }

    for key, extractor in field_map.items():
        if key not in expected:
            continue
        actual_val = extractor(result)
        exp_val    = expected[key]
        if actual_val != exp_val:
            failures.append(f"{key}: expected={exp_val!r}, actual={actual_val!r}")

    return failures


# ── Pretty printer ─────────────────────────────────────────────────────────────

def _print_result(name: str, result: dict[str, Any], failures: list[str],
                  has_expected: bool, error: Optional[str]) -> None:

    print(f"\n{SEP}")
    print(bold(f"  TEST: {name}"))
    print(SEP)

    if error:
        print(red(f"  [EXCEPTION] {error}"))
        return

    # Safety
    safety = result.get("safety", "?")
    colour = green if safety == "safe" else (red if safety == "unsafe" else yellow)
    print(f"  Safety       : {colour(bold(safety.upper()))}")

    # Normalized drugs
    drugs = result.get("normalized_drugs", [])
    if drugs:
        print(f"\n  Normalized Drugs ({len(drugs)}):")
        for d in drugs:
            mg = f"{d['mg_per_day']} mg/day" if d.get("mg_per_day") else dim("no mg/day")
            print(f"    {cyan(d['normalized_name'])}"
                  f"  dose={d.get('dosage_text') or dim('—')}"
                  f"  freq={d.get('frequency_text') or dim('—')}"
                  f"  [{mg}]")
    else:
        print(f"\n  Normalized Drugs : {dim('none')}")

    # Interactions
    interactions = result.get("interactions", [])
    if interactions:
        print(f"\n  Interactions ({len(interactions)}):")
        for ix in interactions:
            sev_colour = red if ix["severity"] == "high" else yellow
            print(f"    {sev_colour(ix['drug_a'])} + {sev_colour(ix['drug_b'])}"
                  f"  [{sev_colour(ix['severity'])}]  {dim(ix['effect'])}")
    else:
        print(f"\n  Interactions     : {dim('none')}")

    # Dosage issues
    dosage = result.get("dosage_issues", [])
    if dosage:
        print(f"\n  Dosage Issues ({len(dosage)}):")
        for d in dosage:
            print(f"    {red(d['drug'])} -> {red(d['issue'])}"
                  f"  parsed={d.get('parsed_mg_per_day')} mg/day"
                  f"  max={d.get('max_mg_per_day')} mg/day")
    else:
        print(f"\n  Dosage Issues    : {dim('none')}")

    # Allergy alerts
    allergy = result.get("allergy_alerts", [])
    if allergy:
        print(f"\n  Allergy Alerts ({len(allergy)}):")
        for a in allergy:
            print(f"    {red(a['allergen'])} -> {red(a['drug'])}"
                  f"  [{a['severity']}]  {dim(a['recommendation'])}")
    else:
        print(f"\n  Allergy Alerts   : {dim('none')}")

    # Alternatives
    alts = result.get("alternatives", [])
    if alts:
        print(f"\n  Alternatives ({len(alts)}):")
        for alt in alts:
            print(f"    {dim(alt['original_drug'])} -> {green(alt['suggested_drug'])}"
                  f"  {dim(alt.get('reason',''))}")
    else:
        print(f"\n  Alternatives     : {dim('none')}")

    # Unknowns
    unknowns = result.get("unknowns", [])
    if unknowns:
        print(f"\n  Unknowns ({len(unknowns)}):")
        for u in unknowns:
            print(f"    {yellow(u['type'])} ({u['value']}): {dim(u['reason'])}")
    else:
        print(f"\n  Unknowns         : {dim('none')}")

    # Pass / Fail verdict
    print(f"\n  {THIN}")
    if not has_expected:
        print(f"  {dim('[NO EXPECTED BLOCK — observation only]')}")
    elif failures:
        print(f"  {red('[FAIL]')}  Reasons:")
        for f in failures:
            print(f"    {red('x')} {f}")
    else:
        print(f"  {green('[PASS]')}")


# ── Main runner ────────────────────────────────────────────────────────────────

def run_tests(filter_str: Optional[str] = None, fail_fast: bool = False) -> None:
    # Use the combined, validated test cases discovered earlier
    test_cases: list[dict] = combined_test_cases
    if not test_cases:
        print(red("No valid regression test files found."))
        sys.exit(1)

    if filter_str:
        test_cases = [tc for tc in test_cases
                      if filter_str.lower() in tc.get("name", "").lower()]
        print(cyan(f"\nFiltered to {len(test_cases)} test(s) matching '{filter_str}'"))

    total     = len(test_cases)
    passed    = 0
    failed    = 0
    errored   = 0
    no_expect = 0
    suite_start = time.perf_counter()

    for case in test_cases:
        name    = case.get("name", "Unnamed Test")
        error   = None
        result  = {}
        failures: list[str] = []

        payload = {
            "prescription_text": case.get("prescription", ""),
            "patient": {
                "age":                 case.get("age", 30),
                "gender":              case.get("gender", "male"),
                "allergies":           case.get("allergies", []),
                "current_medications": case.get("current_medications", []),
            },
        }

        try:
            response = client.post("/verify", json=payload)
            response.raise_for_status()
            result = response.json()
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            errored += 1
            failed  += 1
            _print_result(name, result, [], False, error)
            if fail_fast:
                print(red("\n[FAIL-FAST] Stopping after first failure."))
                break
            continue

        expected    = case.get("expected")
        has_expected = expected is not None

        if has_expected:
            failures = _validate(result, expected)
            if failures:
                failed += 1
            else:
                passed += 1
        else:
            no_expect += 1

        _print_result(name, result, failures, has_expected, None)

        if fail_fast and failures:
            print(red("\n[FAIL-FAST] Stopping after first failure."))
            break

    # ── Summary ────────────────────────────────────────────────────────────────
    elapsed = time.perf_counter() - suite_start
    validated = passed + failed - errored

    print(f"\n{SEP}")
    print(bold("  REGRESSION SUITE SUMMARY"))
    print(SEP)
    print(f"  Total tests run    : {total}")
    print(f"  With expected block: {validated + errored}")
    print(f"  {green('Passed')}             : {green(str(passed))}")
    print(f"  {red('Failed')}             : {red(str(failed))}")
    print(f"  {dim('Observation only')}   : {no_expect}")
    print(f"  Execution time     : {elapsed:.3f}s")
    print(SEP)

    sys.exit(0 if failed == 0 else 1)


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SafeDose Regression Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--filter", "-f",
        metavar="PATTERN",
        help="Only run tests whose name contains PATTERN (case-insensitive).",
    )
    parser.add_argument(
        "--fail-fast", "-x",
        action="store_true",
        help="Stop after the first failing test.",
    )
    args = parser.parse_args()
    run_tests(filter_str=args.filter, fail_fast=args.fail_fast)
