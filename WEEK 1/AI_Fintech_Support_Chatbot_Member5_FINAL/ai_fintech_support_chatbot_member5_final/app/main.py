from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .config import APP_NAME, MODEL_NAME, INTENTS
from .model_service import classify_query, InputValidationError

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title=APP_NAME,
    version="1.0.0",
    description="Hugging Face Transformers fintech customer-support intent classifier and response router.",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    message: str = Field(..., description="Customer support message")


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": APP_NAME,
        "model": MODEL_NAME,
        "supported_intents": len(INTENTS),
    }


@app.post("/api/chat")
def chat(request: ChatRequest):
    try:
        return classify_query(request.message)
    except InputValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "The AI model could not process the request. On first run, make sure the computer "
                "has internet access so Hugging Face can download the model. "
                f"Technical detail: {type(exc).__name__}"
            ),
        )
