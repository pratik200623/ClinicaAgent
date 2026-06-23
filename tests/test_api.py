import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "ClinicaAgent API"}

def test_intake_validation():
    # Empty query should return validation error
    response = client.post("/api/intake", json={"query": ""})
    assert response.status_code == 400

def test_intake_streaming():
    # A valid request should initiate a SSE stream
    response = client.post("/api/intake", json={"query": "EGFR T790M lung cancer in California"})
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    
    # Read the first few lines of the stream
    stream_content = []
    # TestClient supports reading bytes in chunks
    for chunk in response.iter_lines():
        if chunk:
            decoded_chunk = chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
            if decoded_chunk.startswith("data: "):
                event_data = json.loads(decoded_chunk[6:])
                stream_content.append(event_data)
                # Break early once we see IntakeAgent executing
                if len(stream_content) >= 2:
                    break
                    
    assert len(stream_content) >= 1
    assert stream_content[0]["agent"] == "IntakeAgent"
    assert stream_content[0]["status"] == "processing"

def test_export_pdf_endpoint():
    payload = {
        "physician_name": "Dr. Jane Doe",
        "license_number": "MD-999999",
        "patient_query": "Test Query",
        "edited_synthesis": "Test Synthesis Report",
        "approved_trials": [
            {
                "nct_id": "NCT01234567",
                "phase": "Phase 3",
                "title": "A Great Trial",
                "sponsor": "Sponsor Inc.",
                "summary": "This is a great trial.",
                "locations": ["California"],
                "age_range": "18-99",
                "gender_requirement": "ALL",
                "url": "http://trial-url"
            }
        ],
        "approved_genomics": [
            {
                "variant": "EGFR T790M",
                "gene": "EGFR",
                "clinical_significance": "Pathogenic",
                "clinvar_id": "16613",
                "title": "EGFR:T790M record",
                "url": "http://clinvar-url",
                "status": "Found"
            }
        ],
        "approved_literature": [
            {
                "pmid": "42299598",
                "title": "EGFR T790M NSCLC treatment paper",
                "journal": "Nature",
                "date": "2026",
                "authors": "Author A, Author B",
                "url": "http://pub-url"
            }
        ]
    }
    response = client.post("/api/export-pdf", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment; filename=clinical_report.pdf" in response.headers["content-disposition"]
    pdf_content = b"".join(response.iter_bytes())
    assert pdf_content.startswith(b"%PDF-")


def test_translate_endpoint():
    payload = {
        "text": "Hello, this is a test clinical report.",
        "target_lang": "es"
    }
    response = client.post("/api/translate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "translated_text" in data
    assert len(data["translated_text"]) > 0


