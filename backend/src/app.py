"""Interview Copilot Backend API."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Interview Copilot")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok"}


# Offline endpoints
@app.post("/offline/analyze")
def analyze_candidate(x_profile_url: str, resume_text: str, job_description: str):
    """Analyze candidate: X profile vs resume inconsistencies."""
    # TODO: implement
    return {"inconsistencies": [], "technical_competence": []}


# Online endpoints
@app.post("/online/process")
def process_transcript(transcript: str, session_id: str):
    """Process live transcript, detect inconsistencies."""
    # TODO: implement
    return {"flags": [], "suggestions": []}
