# Rule-Based Prescription Safety Workflow

This document describes the current backend after the deterministic clinical decision support refactor.

## Core Rule

The medical decision logic is deterministic and dataset-driven.

The `/verify` flow does not use LLMs, AI reasoning, keyword severity inference, or invented medical facts.

Allowed clinical datasets:

```text
backend/data/interactions.json
backend/data/dosage_rules.json
backend/data/alternatives.json
backend/data/allergy_map.json
```

If required data is missing, the system returns an `UNKNOWN` item instead of guessing.

## Active Backend Structure

```text
backend/main.py
backend/api/routes.py
backend/models/schemas.py
backend/services/normalization_service.py
backend/services/interaction_service.py
backend/services/dosage_service.py
backend/services/patient_service.py
backend/services/recommendation_service.py
backend/services/safety_service.py
backend/services/data_loader.py
```

The existing launcher still works because `backend/app/main.py` imports the new `backend.main:app`.

## API

Main endpoint:

```text
POST /verify
```

Response shape:

```json
{
  "safety": "safe|caution|unsafe|unknown",
  "interactions": [],
  "dosage_issues": [],
  "allergy_alerts": [],
  "alternatives": [],
  "unknowns": [],
  "normalized_drugs": []
}
```

OCR endpoint retained for image extraction:

```text
POST /extract-text
```

OCR is only text extraction. It is not medical decision logic.

## Processing Workflow

1. Receive patient data and prescription text.
2. Extract dataset-known drugs from prescription text.
3. Normalize drug names using:
   - lowercase/trim/noise removal
   - brand-to-generic mapping from `dosage_rules.json`
   - exact dataset match
   - rapidfuzz fuzzy match at high confidence
4. Merge prescribed drugs with patient current medications.
5. Categorize age:
   - `child`: under 18
   - `adult`: 18 to 65
   - `elderly`: over 65
6. Check drug-drug interactions from `interactions.json`.
7. Parse dosage into mg/day and compare against `dosage_rules.json`.
8. Check patient allergies using `allergy_map.json`.
9. Generate alternatives only from `alternatives.json`.
10. Validate alternatives against all other drugs.
11. Compute final safety.
12. Return structured, traceable output.

## Interaction Logic

Service:

```text
backend/services/interaction_service.py
```

Each pair is checked against `interactions.json`.

Dataset entry format:

```json
{
  "drug1|drug2": {
    "severity": "high|moderate|low",
    "mechanism": "...",
    "effect": "...",
    "recommendation": "...",
    "source_id": "..."
  }
}
```

Severity is read directly from the dataset.

If a pair is not present, an `UNKNOWN` item is returned.

## Dosage Logic

Service:

```text
backend/services/dosage_service.py
```

Supported parsing examples:

```text
500mg twice daily
20mg once daily
```

The parser converts dose and frequency into `mg/day`.

Supported frequencies:

```text
once daily, daily, twice daily, bid, three times daily, thrice daily, tid, qid
```

Rules are read from `dosage_rules.json`.

If the drug, age category, range, dosage, or frequency cannot be resolved, an `UNKNOWN` item is returned.

## Allergy Logic

Service:

```text
backend/services/patient_service.py
```

Patient allergies are checked against `allergy_map.json`.

If an allergy is not present in the dataset, the system returns `UNKNOWN`.

## Alternatives Logic

Service:

```text
backend/services/recommendation_service.py
```

Alternatives are only read from `alternatives.json`.

Before an alternative is returned, it is validated against all other current drugs.

If the dataset does not contain enough interaction data to prove the alternative safe, the alternative is not returned and an `UNKNOWN` validation item is reported.

## Safety Logic

Service:

```text
backend/services/safety_service.py
```

Safety rules:

- `unsafe`: any high-severity interaction, dosage issue, or allergy alert
- `unknown`: missing required data and no high-severity issue
- `caution`: moderate interactions, dosage issues, or allergy alerts
- `safe`: no issues and no unknowns

## Frontend

Frontend file:

```text
frontend/app.py
```

The frontend sends:

```json
{
  "patient": {
    "age": 45,
    "gender": "male",
    "conditions": [],
    "allergies": [],
    "current_medications": []
  },
  "drugs": [],
  "text_input": "..."
}
```

The frontend displays:

- extracted/normalized drugs
- interaction signals
- dosage guidance
- alternative suggestions
- allergy alerts
- unknown dataset gaps

## Dependencies

The deterministic fuzzy normalization uses:

```text
rapidfuzz
```

Medical decisions still come only from the JSON datasets.
