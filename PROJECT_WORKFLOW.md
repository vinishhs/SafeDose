# Prescription Verifier Project Workflow

This document explains how this project actually works based on the current codebase.

## Active Entry Points

The project is started by `run-project.ps1`.

It starts two services:

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
python -m streamlit run frontend\app.py --server.port 8501 --server.headless true
```

Active services:

- Backend API: `http://127.0.0.1:8000`
- Frontend UI: `http://127.0.0.1:8501`

The active backend module is:

```text
backend/app/main.py
```

The active frontend module is:

```text
frontend/app.py
```

## Important Truth About The Core Logic

The main prescription verification flow is rule-based.

The active `/verify` endpoint does not use a live medical database, external drug API, or AI model to find interactions.

Drug interactions, dosage recommendations, and alternatives are currently checked using hardcoded Python dictionaries in:

```text
backend/app/drug_utils.py
```

There is an optional IBM Granite endpoint in the backend, but the current frontend does not call it for the main prescription analysis.

## Main Backend API Flow

The main endpoint is:

```text
POST /verify
```

Defined in:

```text
backend/app/main.py
```

The endpoint receives a `PrescriptionRequest` containing:

- patient information
- a list of drugs
- optional raw prescription text

The request model is defined in:

```text
backend/app/models.py
```

Relevant models:

```python
class Drug(BaseModel):
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None

class Patient(BaseModel):
    age: int
    gender: str = "male"
    weight_kg: Optional[float] = None
    conditions: List[str] = []
    allergies: List[str] = []
    current_medications: List[str] = []

class PrescriptionRequest(BaseModel):
    patient: Patient
    drugs: List[Drug]
    text_input: Optional[str] = None
```

## Drug Extraction Logic

Drug extraction happens in:

```text
backend/app/nlp_utils.py
```

Function:

```python
extract_drugs_from_text(prescription_text)
```

This is not machine learning NLP. It uses:

1. A predefined list of common drug names.
2. Regex pattern matching.
3. Simple dosage extraction.
4. Simple frequency extraction.
5. Duplicate removal by drug name.

The predefined drug list is `COMMON_DRUGS`.

Examples of drugs in that list:

- aspirin
- ibuprofen
- metformin
- atorvastatin
- simvastatin
- warfarin
- amoxicillin
- azithromycin
- clarithromycin
- doxycycline

The extractor checks whether each known drug name appears in the lowercased prescription text.

For each found drug, it tries to extract:

- name
- dosage
- frequency

Example output:

```python
{
    "name": "Atorvastatin",
    "dosage": "20mg",
    "frequency": "daily"
}
```

It also checks regex patterns for formats like:

```text
Atorvastatin 20mg daily
Take Amoxicillin 500mg
Rx: Ibuprofen 400mg
```

After extraction, duplicate drugs are removed by drug name.

## Core Drug Interaction Logic

Drug interaction checking happens in:

```text
backend/app/drug_utils.py
```

Function:

```python
check_interactions(drug_list, patient_age)
```

The interaction data is stored in the `drug_interactions` dictionary.

Current interaction pairs include:

```python
("atorvastatin", "clarithromycin")
("aspirin", "ibuprofen")
("warfarin", "ibuprofen")
("lisinopril", "ibuprofen")
("metformin", "ibuprofen")
("simvastatin", "clarithromycin")
("digoxin", "clarithromycin")
```

The interaction checker:

1. Converts all drug names to lowercase.
2. Compares every drug with every other drug.
3. Builds a pair like `(drug_a, drug_b)`.
4. Also builds the reverse pair `(drug_b, drug_a)`.
5. Checks whether either pair exists in `drug_interactions`.
6. If found, creates an `InteractionAlert`.

This means these are treated the same:

```text
Atorvastatin + Clarithromycin
Clarithromycin + Atorvastatin
```

Severity is determined by keyword matching in the interaction description.

Severity is `"high"` if the description contains one of these words:

- bleeding
- damage
- serious
- toxicity

Otherwise, severity is `"medium"`.

Although `patient_age` is passed into `check_interactions()`, the current interaction logic does not use age.

## Dosage Logic

Dosage checking happens in:

```text
backend/app/drug_utils.py
```

Function:

```python
check_dosage(drug, patient_age)
```

The dosage data is stored in:

```python
age_dosage_recommendations
```

The current logic only separates patients into:

```python
"child" if patient_age < 18 else "adult"
```

If a drug exists in `age_dosage_recommendations`, the app returns an age-appropriate dosage recommendation.

Special cases:

- Aspirin under 18 creates a contraindication alert.
- Atorvastatin under 18 creates a not-recommended alert.

Important: the app currently does not parse whether the submitted dose is too high or too low. It returns recommendation alerts based on age and known drug name.

## Alternative Suggestion Logic

Alternative suggestions happen in:

```text
backend/app/drug_utils.py
```

Function:

```python
get_alternatives(drug, patient, reason)
```

The alternatives are stored in:

```python
alternative_drugs
```

Example:

```python
"atorvastatin": ["rosuvastatin", "simvastatin", "pravastatin"]
"clarithromycin": ["azithromycin", "amoxicillin", "doxycycline", "levofloxacin"]
```

Alternatives are generated after interactions and dosage alerts are found.

For each alert, the backend picks a target drug:

- For interaction alerts, it uses `alert.drug_a`.
- For dosage alerts, it uses `alert.drug`.

Then it calls `get_alternatives()`.

The reason text is copied from the alert description or issue.

## Safety Decision

The final safety result is computed in:

```text
backend/app/main.py
```

Logic:

```python
is_safe = not (interaction_alerts or dosage_alerts)
```

So:

- If there are no interaction alerts and no dosage alerts, `is_safe = True`.
- If there is at least one interaction alert or dosage alert, `is_safe = False`.

## Backend Response

The backend returns a `VerificationResponse`.

Defined in:

```text
backend/app/models.py
```

Response fields:

```python
class VerificationResponse(BaseModel):
    is_safe: bool
    interactions: List[InteractionAlert] = []
    dosage_alerts: List[DosageAlert] = []
    alternatives: List[AlternativeSuggestion] = []
    extracted_drugs: List[Drug] = []
```

The frontend displays these response fields in separate result panels.

## OCR Workflow

OCR is used when the user uploads a prescription image.

Frontend function:

```python
extract_text_from_image_api(uploaded_file)
```

Located in:

```text
frontend/app.py
```

It sends the uploaded image to:

```text
POST http://localhost:8000/extract-text
```

Backend endpoint:

```python
@app.post("/extract-text")
```

Located in:

```text
backend/app/main.py
```

The backend uses:

```text
backend/app/ocr_processor.py
```

OCR libraries used:

- PIL / Pillow
- OpenCV
- NumPy
- pytesseract
- Tesseract executable installed on the machine

OCR processing steps:

1. Read uploaded image bytes.
2. Open image using Pillow.
3. Convert image to a NumPy/OpenCV image.
4. Convert image to grayscale.
5. Apply thresholding.
6. Apply median blur.
7. Run `pytesseract.image_to_string()`.
8. Return extracted text.

If backend OCR fails or returns no text, the frontend has a local fallback OCR path using:

- OpenCV
- NumPy
- pytesseract

## Frontend Workflow

The frontend is:

```text
frontend/app.py
```

The UI is built with Streamlit.

The user provides:

- age
- gender
- medical conditions
- allergies
- current medications

The user chooses one prescription input method:

1. Upload image
2. Manual text

### Upload Flow

If the user chooses Upload:

1. User uploads an image.
2. User clicks `Extract Text From Image`.
3. Frontend sends the image to backend `/extract-text`.
4. Backend performs OCR.
5. Extracted text is returned.
6. Frontend shows the extracted text in an editable text area.
7. User can edit OCR text before analysis.

### Manual Flow

If the user chooses Manual:

1. User types or pastes prescription text.
2. No OCR is used.
3. The typed text is sent directly to the backend for verification.

### Analysis Flow

When the user clicks `Analyze Prescription`:

1. Frontend validates that there is prescription text.
2. Frontend builds `patient_context`.
3. Frontend builds this payload:

```python
payload = {
    "patient": patient_context,
    "drugs": [],
    "text_input": text,
}
```

4. Frontend sends the payload to:

```text
POST http://localhost:8000/verify
```

5. Backend extracts drugs.
6. Backend checks interactions.
7. Backend checks dosage guidance.
8. Backend generates alternatives.
9. Backend returns the response.
10. Frontend stores the response in Streamlit session state.
11. Frontend renders the result panels.

## Frontend Result Display

The frontend displays:

- Extracted Drugs
- Interaction Signals
- Dosage Guidance
- Alternative Suggestions

Before displaying, the frontend removes duplicate output using:

```python
unique_items()
```

Located in:

```text
frontend/app.py
```

Current deduplication rules:

- Extracted drugs are unique by name, dosage, and frequency.
- Dosage alerts are unique by drug, issue, and recommended dosage.
- Interactions are unique by drug pair and description.
- Alternatives are unique by original drug and suggested drug.

This means the same alternative is shown only once even if multiple alerts produce it.

## Optional IBM Granite Endpoint

There is an optional IBM Granite medical analysis module:

```text
backend/app/granite_medical.py
```

Endpoint:

```text
POST /granite-analysis
```

This module uses:

- `transformers`
- `torch`
- `ibm-granite/granite-3.3-2b-instruct`

It creates a prompt asking the model to analyze:

- potential drug interactions
- age-appropriate dosage considerations
- alternative medication suggestions
- safety recommendations

Important: this endpoint is not used by the current frontend analysis flow. The main app uses `/verify`, which is rule-based.

## Files That Matter Most

```text
run-project.ps1
frontend/app.py
backend/app/main.py
backend/app/models.py
backend/app/nlp_utils.py
backend/app/drug_utils.py
backend/app/ocr_processor.py
backend/app/granite_medical.py
```

## Current Limitations

This project is a prototype.

Important limitations:

- Drug interaction data is hardcoded.
- No external clinical drug database is used.
- The main verification flow does not use AI.
- Dosage checking gives age-based recommendations but does not deeply validate submitted dose strength.
- Patient allergies, conditions, current medications, gender, and weight are collected but are not deeply used in the current rule logic.
- OCR quality depends on image clarity and local Tesseract installation.
- The optional Granite endpoint may require internet access, model download, and enough system memory.
- Results should be treated as educational support only, not clinical advice.

## Complete End-To-End Workflow

1. User starts the project with `.\run-project.ps1`.
2. PowerShell starts FastAPI backend on port `8000`.
3. PowerShell starts Streamlit frontend on port `8501`.
4. User opens the frontend.
5. User enters patient details.
6. User either uploads a prescription image or enters prescription text manually.
7. If image is uploaded, frontend sends it to `/extract-text`.
8. Backend OCR extracts text using OpenCV and Tesseract.
9. Frontend receives OCR text and allows editing.
10. User clicks `Analyze Prescription`.
11. Frontend sends patient context and prescription text to `/verify`.
12. Backend extracts drug names, dosage, and frequency from text.
13. Backend checks all drug pairs against the hardcoded interaction dictionary.
14. Backend checks each drug against age-based dosage recommendation rules.
15. Backend generates alternatives for drugs involved in alerts.
16. Backend computes `is_safe`.
17. Backend returns extracted drugs, interactions, dosage alerts, alternatives, and safety status.
18. Frontend deduplicates repeated display items.
19. Frontend displays the final report in result panels.
20. User reviews the output.
