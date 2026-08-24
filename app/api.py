from fastapi import FastAPI, HTTPException

from app.analyzer import AnalysisError
from app.config import get_settings
from app.models import AnalysisResult, TicketRequest
from app.service import service

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    description="AI ticket triage, routing, and reply drafting webhook.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "provider": "ollama", "model": settings.ollama_model}


@app.post("/webhooks/tickets", response_model=AnalysisResult)
def analyze_ticket(ticket: TicketRequest) -> AnalysisResult:
    try:
        return service.analyze(ticket)
    except AnalysisError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

