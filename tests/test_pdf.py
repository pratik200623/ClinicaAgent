import pytest
from backend.utils.pdf_generator import generate_clinical_pdf, clean_text

def test_clean_text():
    # Verify markdown bold conversion
    text = "This is **bold** and *italic*."
    cleaned = clean_text(text)
    assert "<b>bold</b>" in cleaned
    assert "<i>italic</i>" in cleaned

    # Verify double newline handling
    multiline = "Para 1\n\nPara 2"
    cleaned_multiline = clean_text(multiline)
    assert "Para 1<br/><br/>Para 2" in cleaned_multiline

def test_generate_clinical_pdf():
    physician_name = "Dr. Jane Doe"
    license_number = "MD-999999"
    patient_query = "58yo male diagnosed with non-small cell lung cancer with EGFR T790M mutation in California"
    edited_synthesis = "This is a **clinical synthesis** report."
    
    approved_trials = [
        {
            "nct_id": "NCT01234567",
            "phase": "Phase 3",
            "title": "A Great Trial",
            "sponsor": "Sponsor Inc.",
            "summary": "This is a great trial.",
            "locations": ["California", "New York"],
            "age_range": "18-99",
            "gender_requirement": "ALL"
        }
    ]
    
    approved_genomics = [
        {
            "variant": "EGFR T790M",
            "gene": "EGFR",
            "clinical_significance": "Pathogenic",
            "clinvar_id": "16613",
            "title": "EGFR:T790M record"
        }
    ]
    
    approved_literature = [
        {
            "pmid": "42299598",
            "title": "EGFR T790M NSCLC treatment paper",
            "journal": "Nature",
            "date": "2026",
            "authors": "Author A, Author B"
        }
    ]

    pdf_bytes = generate_clinical_pdf(
        physician_name=physician_name,
        license_number=license_number,
        patient_query=patient_query,
        edited_synthesis=edited_synthesis,
        approved_trials=approved_trials,
        approved_genomics=approved_genomics,
        approved_literature=approved_literature
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    # PDF files start with %PDF- header
    assert pdf_bytes.startswith(b"%PDF-")
