import logging
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List, Optional
from pydantic import BaseModel
from .agents.coordinator import run_orchestration_stream
from .utils.pdf_generator import generate_clinical_pdf

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(
    title="ClinicaAgent API",
    description="Multi-agent clinical trial matching and genomic intelligence system.",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In development, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

class ExportPDFRequest(BaseModel):
    physician_name: str
    license_number: str
    patient_query: str
    edited_synthesis: str
    approved_trials: List[dict]
    approved_genomics: List[dict]
    approved_literature: List[dict]

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "ClinicaAgent API"}

@app.post("/api/intake")
async def handle_intake(request: QueryRequest):
    """
    Accepts a patient profile query and streams real-time logs and results
    from the multi-agent system using Server-Sent Events (SSE).
    """
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
        
    logger.info(f"Received query request: {query}")
    
    async def sse_generator():
        async for event in run_orchestration_stream(query):
            # Format as SSE event
            yield f"data: {event}\n"
            
    return StreamingResponse(sse_generator(), media_type="text/event-stream")

@app.post("/api/export-pdf")
async def export_pdf(request: ExportPDFRequest):
    """
    Generates and returns a verified clinical summary report PDF.
    """
    logger.info(f"Generating clinical report PDF for physician: {request.physician_name}")
    try:
        pdf_bytes = generate_clinical_pdf(
            physician_name=request.physician_name,
            license_number=request.license_number,
            patient_query=request.patient_query,
            edited_synthesis=request.edited_synthesis,
            approved_trials=request.approved_trials,
            approved_genomics=request.approved_genomics,
            approved_literature=request.approved_literature
        )
        import io
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=clinical_report.pdf"}
        )
    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)

