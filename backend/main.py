from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router


app = FastAPI(
    title="Rule-Based Prescription Safety API",
    version="2.0.0",
    description="Deterministic clinical decision support using structured JSON datasets.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Rule-based Prescription Safety API is running.",
        "medical_logic": "deterministic_dataset_rules_only",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
