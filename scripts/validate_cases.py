import sys
import json
from fastapi.testclient import TestClient
# Ensure project root is on sys.path
sys.path.insert(0, '.')
from backend.main import app

client = TestClient(app)

cases = [
    {
        "name": "Case 1 Interaction",
        "prescription": "prescribe clarithromycin 500mg twice daily",
        "allergies": [],
        "current_medications": ["atorvastatin"]
    },
    {
        "name": "Case 2 Dosage Parse",
        "prescription": "prescribe paracetamol",
        "allergies": [],
        "current_medications": []
    },
    {
        "name": "Case 3 No Parse Current",
        "prescription": "prescribe ibuprofen",
        "allergies": [],
        "current_medications": ["metformin"]
    }
]

for c in cases:
    payload = {
        "prescription_text": c["prescription"],
        "patient": {
            "age": 30,
            "gender": "male",
            "allergies": c.get("allergies", []),
            "current_medications": c.get("current_medications", [])
        }
    }
    resp = client.post("/verify", json=payload)
    print(f"\n=== {c['name']} ===")
    print(json.dumps(resp.json(), indent=2))
