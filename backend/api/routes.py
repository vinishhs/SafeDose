from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from backend.models.schemas import UnknownItem, VerifyRequest, VerifyResponse
from backend.services.dosage_service import check_dosage
from backend.services.interaction_service import check_interactions
from backend.services.normalization_service import extract_drug_inputs
from backend.services.patient_service import age_category, check_allergies, merge_with_current_medications
from backend.services.recommendation_service import suggest_alternatives
from backend.services.safety_service import compute_safety


router = APIRouter()


@router.post("/verify", response_model=VerifyResponse)
async def verify_prescription(request: VerifyRequest) -> VerifyResponse:
    prescription_text = request.prescription_text or request.text_input or ""
    prescribed = [*request.drugs, *extract_drug_inputs(prescription_text)]

    unknowns: list[UnknownItem] = []
    if not prescribed:
        unknowns.append(
            UnknownItem(
                type="prescription",
                value="UNKNOWN",
                reason="No dataset-recognized prescribed drugs were found in the request.",
                source="request",
            )
        )

    normalized_drugs, normalization_unknowns = merge_with_current_medications(
        prescribed,
        request.patient.current_medications,
    )
    unknowns.extend(normalization_unknowns)

    category = age_category(request.patient.age)

    interactions, interaction_unknowns = check_interactions(normalized_drugs)
    unknowns.extend(interaction_unknowns)

    dosage_issues, dosage_unknowns = check_dosage(normalized_drugs, category)
    unknowns.extend(dosage_unknowns)

    allergy_alerts, allergy_unknowns = check_allergies(request.patient, normalized_drugs)
    unknowns.extend(allergy_unknowns)

    alternatives, alternative_unknowns = suggest_alternatives(
        request.patient,
        normalized_drugs,
        interactions,
        dosage_issues,
        allergy_alerts,
    )
    unknowns.extend(alternative_unknowns)

    safety = compute_safety(interactions, dosage_issues, allergy_alerts, unknowns)

    return VerifyResponse(
        safety=safety,
        interactions=interactions,
        dosage_issues=dosage_issues,
        allergy_alerts=allergy_alerts,
        alternatives=alternatives,
        unknowns=_dedupe_unknowns(unknowns),
        normalized_drugs=normalized_drugs,
    )


def _dedupe_unknowns(unknowns: list[UnknownItem]) -> list[UnknownItem]:
    deduped: list[UnknownItem] = []
    seen = set()
    for item in unknowns:
        key = (item.type, item.value, item.reason, item.source)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


@router.post("/extract-text")
async def extract_text_from_image(image_file: UploadFile = File(...)) -> JSONResponse:
    try:
        from backend.app.ocr_processor import ocr_processor
    except ImportError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": f"OCR dependencies are unavailable: {exc}",
            },
        )

    try:
        image_data = await image_file.read()
        extracted_text = ocr_processor.extract_text_from_image(image_data)
        return JSONResponse(content={"success": True, "extracted_text": extracted_text})
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(exc)},
        )
