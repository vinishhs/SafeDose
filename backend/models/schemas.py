from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


Severity = Literal["high", "moderate", "low", "unknown"]
SafetyStatus = Literal["safe", "caution", "unsafe", "unknown"]


class DrugInput(BaseModel):
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    source: str = "input"


class PatientInput(BaseModel):
    age: int
    gender: str = "unknown"
    allergies: List[str] = Field(default_factory=list)
    current_medications: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)


class VerifyRequest(BaseModel):
    patient: PatientInput
    prescription_text: Optional[str] = None
    text_input: Optional[str] = None
    drugs: List[DrugInput] = Field(default_factory=list)


class NormalizedDrug(BaseModel):
    original_name: str
    normalized_name: str
    dosage_text: Optional[str] = None
    frequency_text: Optional[str] = None
    mg_per_day: Optional[float] = None
    source: str
    trace: Dict[str, Any] = Field(default_factory=dict)


class UnknownItem(BaseModel):
    type: str
    value: str
    reason: str
    source: str


class InteractionAlert(BaseModel):
    drug_a: str
    drug_b: str
    severity: Severity
    mechanism: str
    effect: str
    recommendation: str
    source_id: str


class DosageIssue(BaseModel):
    drug: str
    severity: Severity
    issue: Literal["overdose", "underdose", "unknown"]
    parsed_mg_per_day: Optional[float] = None
    min_mg_per_day: Optional[float] = None
    max_mg_per_day: Optional[float] = None
    recommendation: str
    source_id: str


class AllergyAlert(BaseModel):
    allergen: str
    drug: str
    severity: Severity
    recommendation: str
    source_id: str


class AlternativeSuggestion(BaseModel):
    original_drug: str
    suggested_drug: str
    reason: str
    validation_status: Literal["safe", "unknown"]
    source_id: str


class VerifyResponse(BaseModel):
    safety: SafetyStatus
    interactions: List[InteractionAlert] = Field(default_factory=list)
    dosage_issues: List[DosageIssue] = Field(default_factory=list)
    allergy_alerts: List[AllergyAlert] = Field(default_factory=list)
    alternatives: List[AlternativeSuggestion] = Field(default_factory=list)
    unknowns: List[UnknownItem] = Field(default_factory=list)
    normalized_drugs: List[NormalizedDrug] = Field(default_factory=list)
