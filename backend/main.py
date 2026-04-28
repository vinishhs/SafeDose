from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import tempfile
import os

# Import from your actual files
from .models import PrescriptionRequest, VerificationResponse
from .npl_utils import extract_drugs_from_text
from .drug_utils import check_interactions, check_dosage, get_alternatives  # Changed from drug_checker to drug_utils
from .speech_processor import speech_processor  # If you have this

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MedSafe AI API", version="1.0.0")

# Configure CORS to allow requests from the Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # Streamlit's default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/verify")
async def verify_prescription(request: PrescriptionRequest):
    """Main endpoint to verify a prescription."""
    try:
        drugs_to_check = request.drugs

        # 1. Extract drugs from text if provided
        if request.text_input:
            extracted_drugs = extract_drugs_from_text(request.text_input)
            logger.info(f"Extracted drugs from text: {extracted_drugs}")
            # Convert extracted drugs to Drug objects if needed
            from .models import Drug
            for drug_info in extracted_drugs:
                drugs_to_check.append(Drug(
                    name=drug_info.get('name', ''),
                    dosage=drug_info.get('dosage', ''),
                    frequency=drug_info.get('frequency', '')
                ))

        if not drugs_to_check:
            return VerificationResponse(
                is_safe=True,
                extracted_drugs=[],
                interactions=[],
                dosage_alerts=[],
                alternatives=[]
            )

        # 2. Check for drug interactions
        interaction_alerts = check_interactions(drugs_to_check, request.patient.age)

        # 3. Check dosage for each drug
        dosage_alerts = []
        for drug in drugs_to_check:
            dosage_alerts.extend(check_dosage(drug, request.patient.age))

        # 4. Suggest alternatives for problematic drugs
        alternative_suggestions = []
        for alert in interaction_alerts + dosage_alerts:
            # Find the target drug
            target_drug_name = alert.drug_a if hasattr(alert, 'drug_a') else alert.drug
            target_drug = next((d for d in drugs_to_check if d.name.lower() == target_drug_name.lower()), None)
            if target_drug:
                alts = get_alternatives(target_drug, request.patient, alert.description)
                alternative_suggestions.extend(alts)

        # 5. Determine overall safety
        is_safe = not (interaction_alerts or dosage_alerts)

        return VerificationResponse(
            is_safe=is_safe,
            extracted_drugs=drugs_to_check,
            interactions=interaction_alerts,
            dosage_alerts=dosage_alerts,
            alternatives=alternative_suggestions
        )

    except Exception as e:
        logger.error(f"An error occurred during verification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transcribe-speech")
async def transcribe_speech(audio_file: UploadFile = File(...)):
    """
    Endpoint to transcribe speech audio to text for prescription dictation.
    """
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            content = await audio_file.read()
            temp_audio.write(content)
            temp_audio_path = temp_audio.name
        
        # Transcribe audio
        transcription = speech_processor.transcribe_audio(temp_audio_path)
        
        # Clean up temporary file
        os.unlink(temp_audio_path)
        
        return JSONResponse(content={
            "transcribed_text": transcription,
            "success": True
        })
        
    except Exception as e:
        logger.error(f"Speech transcription error: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/")
async def root():
    return {"message": "MedSafe AI API is running."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)