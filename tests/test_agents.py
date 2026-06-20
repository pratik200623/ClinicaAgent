import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.agents.intake_agent import parse_query, PatientProfile
from backend.agents.clinical_agent import match_clinical_trials
from backend.agents.genomic_agent import interpret_genomic_variants
from backend.agents.literature_agent import search_literature

# 1. Intake Agent Tests
@pytest.mark.asyncio
async def test_intake_agent_lung_cancer():
    query = "58yo male diagnosed with non-small cell lung cancer with EGFR T790M mutation in California"
    profile = await parse_query(query)
    
    assert profile.condition is not None
    assert profile.condition.lower() == "non-small cell lung cancer"
    assert profile.age == 58
    assert profile.gender == "male"
    assert profile.location is not None, "Location should not be None — check intake_agent regex"
    assert profile.location.lower() == "california"
    assert "EGFR T790M" in profile.variants

@pytest.mark.asyncio
async def test_intake_agent_breast_cancer():
    query = "45-year-old female with BRCA1 positive breast cancer near Boston"
    profile = await parse_query(query)
    
    assert profile.condition is not None
    assert profile.condition.lower() == "breast cancer"
    assert profile.age == 45
    assert profile.gender == "female"
    assert profile.location is not None, "Location should not be None — check intake_agent regex"
    assert profile.location.lower() == "boston"
    assert "BRCA1" in profile.variants

# 2. Clinical Agent Test with Mocking
@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_clinical_agent(mock_get):
    # Mock ClinicalTrials.gov response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "studies": [
            {
                "protocolSection": {
                    "identificationModule": {
                        "nctId": "NCT01234567",
                        "briefTitle": "Targeted Therapy Study for Lung Cancer"
                    },
                    "descriptionModule": {
                        "briefSummary": "This is a brief summary of a mock study."
                    },
                    "designModule": {
                        "phases": ["PHASE2"]
                    },
                    "eligibilityModule": {
                        "eligibilityCriteria": "Inclusion: Patients with EGFR mutations...",
                        "minimumAge": "18 Years",
                        "maximumAge": "75 Years",
                        "sex": "ALL"
                    },
                    "sponsorCollaboratorsModule": {
                        "leadSponsor": {"name": "Mock Pharma Inc."}
                    }
                }
            }
        ]
    }
    mock_get.return_value = mock_resp
    
    profile = PatientProfile(
        condition="Lung Cancer",
        age=58,
        gender="male",
        location="California",
        variants=["EGFR T790M"]
    )
    
    results = await match_clinical_trials(profile)
    assert len(results) == 1
    assert results[0]["nct_id"] == "NCT01234567"
    assert results[0]["phase"] == "PHASE2"
    assert results[0]["sponsor"] == "Mock Pharma Inc."

# 3. Genomic Agent Test with Mocking
@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_genomic_agent(mock_get):
    # Mock ClinVar search and summary response
    mock_search_resp = MagicMock()
    mock_search_resp.status_code = 200
    mock_search_resp.json.return_value = {
        "esearchresult": {
            "idlist": ["16618"]
        }
    }
    
    mock_summary_resp = MagicMock()
    mock_summary_resp.status_code = 200
    mock_summary_resp.json.return_value = {
        "result": {
            "16618": {
                "title": "NM_005228.5(EGFR): c.2369C>T (p.Thr790Met)",
                "clinical_significance": {
                    "description": "Pathogenic"
                },
                "genes": [
                    {"symbol": "EGFR"}
                ],
                "variation_set": [
                    {
                        "variation_loc": [
                            {"assembly_name": "GRCh38", "chr": "7", "start": "55181378", "stop": "55181378"}
                        ]
                    }
                ]
            }
        }
    }
    
    # We call get twice: first for search, second for summary
    mock_get.side_effect = [mock_search_resp, mock_summary_resp]
    
    profile = PatientProfile(
        condition="Lung Cancer",
        age=58,
        gender="male",
        location="California",
        variants=["EGFR T790M"]
    )
    
    results = await interpret_genomic_variants(profile)
    assert len(results) == 1
    assert results[0]["variant"] == "EGFR T790M"
    assert results[0]["status"] == "Found"
    assert results[0]["clinical_significance"] == "Pathogenic"
    assert results[0]["gene"] == "EGFR"

# 4. Literature Agent Test with Mocking
@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_literature_agent(mock_get):
    # Mock PubMed search and summary response
    mock_search_resp = MagicMock()
    mock_search_resp.status_code = 200
    mock_search_resp.json.return_value = {
        "esearchresult": {
            "idlist": ["25555555"]
        }
    }
    
    mock_summary_resp = MagicMock()
    mock_summary_resp.status_code = 200
    mock_summary_resp.json.return_value = {
        "result": {
            "25555555": {
                "title": "Efficacy of EGFR inhibitors in T790M mutated lung cancer",
                "pubdate": "2024 Jan 1",
                "source": "Journal of Clinical Oncology",
                "authors": [
                    {"name": "Smit E"}
                ],
                "articleids": [
                    {"idtype": "pmid", "value": "25555555"}
                ]
            }
        }
    }
    
    mock_get.side_effect = [mock_search_resp, mock_summary_resp]
    
    profile = PatientProfile(
        condition="Lung Cancer",
        age=58,
        gender="male",
        location="California",
        variants=["EGFR T790M"]
    )
    
    results = await search_literature(profile)
    assert len(results) == 1
    assert results[0]["pmid"] == "25555555"
    assert results[0]["journal"] == "Journal of Clinical Oncology"
    assert "Smit E" in results[0]["authors"]
