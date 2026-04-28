from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from .models import PrescriptionRequest, VerificationResponse, Drug
from .nlp_utils import extract_drugs_from_text
from .drug_utils import check_interactions, check_dosage, get_alternatives

try:
    from .ocr_processor import ocr_processor
except ImportError:
    ocr_processor = None

try:
    from .granite_medical import granite_medical
except ImportError:
    granite_medical = None


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MedSafe AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/verify")
async def verify_prescription(request: PrescriptionRequest):
    """Main endpoint to verify a prescription."""
    try:
        drugs_to_check = request.drugs

        if request.text_input:
            extracted_drugs = extract_drugs_from_text(request.text_input)
            logger.info("Extracted drugs from text: %s", extracted_drugs)
            for drug_info in extracted_drugs:
                drugs_to_check.append(
                    Drug(
                        name=drug_info.get("name", ""),
                        dosage=drug_info.get("dosage", ""),
                        frequency=drug_info.get("frequency", ""),
                    )
                )

        if not drugs_to_check:
            return VerificationResponse(
                is_safe=True,
                extracted_drugs=[],
                interactions=[],
                dosage_alerts=[],
                alternatives=[],
            )

        interaction_alerts = check_interactions(drugs_to_check, request.patient.age)

        dosage_alerts = []
        for drug in drugs_to_check:
            dosage_alerts.extend(check_dosage(drug, request.patient.age))

        alternative_suggestions = []
        for alert in interaction_alerts + dosage_alerts:
            target_drug_name = alert.drug_a if hasattr(alert, "drug_a") else alert.drug
            target_drug = next(
                (d for d in drugs_to_check if d.name.lower() == target_drug_name.lower()),
                None,
            )
            if target_drug:
                reason = alert.description if hasattr(alert, "description") else alert.issue
                alts = get_alternatives(target_drug, request.patient, reason)
                alternative_suggestions.extend(alts)

        is_safe = not (interaction_alerts or dosage_alerts)

        return VerificationResponse(
            is_safe=is_safe,
            extracted_drugs=drugs_to_check,
            interactions=interaction_alerts,
            dosage_alerts=dosage_alerts,
            alternatives=alternative_suggestions,
        )

    except Exception as e:
        logger.error("An error occurred during verification: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract-text")
async def extract_text_from_image(image_file: UploadFile = File(...)):
    """Endpoint to extract text from prescription image using OCR."""
    try:
        if ocr_processor is None:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "OCR dependencies are not installed on this environment.",
                },
            )

        image_data = await image_file.read()
        extracted_text = ocr_processor.extract_text_from_image(image_data)

        return JSONResponse(
            content={
                "extracted_text": extracted_text,
                "success": True,
            }
        )

    except Exception as e:
        logger.error("OCR extraction error: %s", e)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@app.post("/granite-analysis")
async def granite_medical_analysis(request: PrescriptionRequest):
    """Analyze prescription using IBM Granite model."""
    try:
        if granite_medical is None:
            raise HTTPException(
                status_code=503,
                detail="IBM Granite dependencies are not installed on this environment",
            )

        if not request.text_input:
            raise HTTPException(status_code=400, detail="No text input provided")

        result = granite_medical.generate_medical_advice(
            request.text_input,
            request.patient.age,
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return result

    except Exception as e:
        logger.error("Granite analysis error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {"message": "MedSafe AI API is running."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
