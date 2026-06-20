import httpx
import json
import sys

def verify_sse():
    print("--- Testing SSE Stream (/api/intake) ---")
    payload = {
        "query": "58yo male diagnosed with non-small cell lung cancer with EGFR T790M mutation in California"
    }
    
    results = None
    try:
        # Use a client with no timeout for streaming
        with httpx.Client(timeout=30.0) as client:
            # We use a POST request with streaming response
            with client.stream("POST", "http://127.0.0.1:8000/api/intake", json=payload) as r:
                if r.status_code != 200:
                    print(f"Error: Status code {r.status_code}")
                    return False
                    
                for line in r.iter_lines():
                    if line.strip():
                        if line.startswith("data: "):
                            event_data = json.loads(line[6:])
                            status = event_data.get("status")
                            agent = event_data.get("agent", "")
                            msg = event_data.get("message", "")
                            
                            if status == "processing":
                                print(f"[{agent}] {msg}")
                            elif status == "completed":
                                print(f"[{agent}] Completed: {msg}")
                            elif status == "result":
                                print("[Coordinator] Received final payload.")
                                results = event_data.get("data")
                            elif status == "error":
                                print(f"[Error] {msg}")
                                return False
    except Exception as e:
        print(f"Failed to query backend: {e}")
        return False

    if not results:
        print("Failed to retrieve result payload.")
        return False

    print("SSE Stream verification successful!")
    return results

def verify_pdf(results):
    print("\n--- Testing PDF Export (/api/export-pdf) ---")
    payload = {
        "physician_name": "Dr. Alice Smith",
        "license_number": "LIC-987654",
        "patient_query": "58yo male diagnosed with non-small cell lung cancer with EGFR T790M mutation in California",
        "edited_synthesis": results.get("synthesis", ""),
        "approved_trials": results.get("clinical_trials", []),
        "approved_genomics": results.get("genomics", []),
        "approved_literature": results.get("literature", [])
    }
    
    try:
        r = httpx.post("http://127.0.0.1:8000/api/export-pdf", json=payload, timeout=20.0)
        if r.status_code == 200:
            print("PDF generation call succeeded!")
            pdf_bytes = r.content
            print(f"Received PDF report: {len(pdf_bytes)} bytes.")
            # Let's save a copy in the scratch folder to verify
            import os
            os.makedirs("scratch", exist_ok=True)
            with open("scratch/sample_clinical_report.pdf", "wb") as f:
                f.write(pdf_bytes)
            print("Saved sample report to scratch/sample_clinical_report.pdf")
            return True
        else:
            print(f"Error: Status code {r.status_code}. Response: {r.text}")
            return False
    except Exception as e:
        print(f"Failed to post PDF export: {e}")
        return False

if __name__ == "__main__":
    payload_results = verify_sse()
    if payload_results:
        verify_pdf(payload_results)
    else:
        print("SSE validation failed; skipping PDF validation.")
        sys.exit(1)
