from pydantic import BaseModel
from typing import List, Optional

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

class InteractionAlert(BaseModel):
    drug_a: str
    drug_b: str
    description: str
    severity: str  # "high", "medium", "low"

class DosageAlert(BaseModel):
    drug: str
    issue: str
    recommended_dosage: Optional[str] = None

class AlternativeSuggestion(BaseModel):
    original_drug: str
    suggested_drug: str
    reason: str

class VerificationResponse(BaseModel):
    is_safe: bool
    interactions: List[InteractionAlert] = []
    dosage_alerts: List[DosageAlert] = []
    alternatives: List[AlternativeSuggestion] = []
    extracted_drugs: List[Drug] = []
