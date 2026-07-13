#!/usr/bin/env python3
"""
Validation script for backend/data/alternatives.json
Ensures every alternative entry:
- Has a non‑empty, non‑"UNKNOWN" reason string
- No duplicate alternative for the same original drug
- Original drug and suggested drug are present in the known drug list

The known drug list is derived from backend/data/dosage_rules.json keys.
The script prints a concise report and exits with status 0 if all is well,
otherwise with status 1.
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALTS_PATH = PROJECT_ROOT / "backend" / "data" / "alternatives.json"
DOSAGE_RULES_PATH = PROJECT_ROOT / "backend" / "data" / "dosage_rules.json"

def load_json(p: Path):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    alternatives = load_json(ALTS_PATH)
    dosage_rules = load_json(DOSAGE_RULES_PATH)
    known_drugs = set(dosage_rules.keys())

    total_alts = 0
    issues = []
    for orig, alts in alternatives.items():
        # Validate original drug exists in dosage rules
        if orig not in known_drugs:
            issues.append(f"Invalid original drug: {orig}")
        seen_sugs = set()
        for entry in alts:
            total_alts += 1
            drug = entry.get("drug")
            reason = entry.get("reason")
            # Duplicate suggested drug for same original
            if drug in seen_sugs:
                issues.append(f"Duplicate alternative for {orig}: {drug}")
            else:
                seen_sugs.add(drug)
            # Validate suggested drug exists
            if drug not in known_drugs:
                issues.append(f"Invalid suggested drug for {orig}: {drug}")
            # Reason checks
            if reason is None:
                issues.append(f"Missing reason for alternative {orig} -> {drug}")
            elif isinstance(reason, str):
                stripped = reason.strip()
                if stripped == "" or stripped.upper() == "UNKNOWN":
                    issues.append(f"Bad reason for alternative {orig} -> {drug}: '{reason}'")
            else:
                issues.append(f"Reason not a string for alternative {orig} -> {drug}")

    print("=== Alternatives Validation Report ===")
    print(f"Total original drugs with alternatives: {len(alternatives)}")
    print(f"Total alternative entries examined: {total_alts}")
    if issues:
        print("\nIssues found:")
        for i, msg in enumerate(issues, 1):
            print(f" {i}. {msg}")
        sys.exit(1)
    else:
        print("No issues detected. All alternatives have proper reasons and valid drug names.")
        sys.exit(0)

if __name__ == "__main__":
    main()
