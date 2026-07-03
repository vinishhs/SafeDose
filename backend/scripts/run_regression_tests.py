import json
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

with open("tests/test_cases.json", "r") as f:
    test_cases = json.load(f)

for case in test_cases:
    payload = {
        "prescription_text": case["prescription"],
        "patient": {
            "age": 30,
            "gender": "male",
            "allergies": case["allergies"],
            "current_medications": []
        }
    }

    response = client.post("/verify", json=payload)
    result = response.json()

    print("\n" + "=" * 100)
    print(f"TEST: {case['name']}")
    print("=" * 100)

    print("Safety:")
    print(result.get("safety"))

    print("\nNormalized Drugs:")
    for drug in result.get("normalized_drugs", []):
        print(
            f"{drug['normalized_name']} | "
            f"dose={drug['dosage_text']} | "
            f"freq={drug['frequency_text']} | "
            f"mg/day={drug['mg_per_day']}"
        )

    print("\nInteractions:")
    for i in result.get("interactions", []):
        print(f"{i['drug_a']} + {i['drug_b']}")

    print("\nDosage Issues:")
    for d in result.get("dosage_issues", []):
        print(f"{d['drug']} -> {d['issue']}")

    print("\nAllergy Alerts:")
    for a in result.get("allergy_alerts", []):
        print(f"{a['allergen']} -> {a['drug']}")

    print("\nUnknowns:")
    for u in result.get("unknowns", []):
        print(f"{u['type']} ({u['value']}): {u['reason']}")