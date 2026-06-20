import httpx
import logging
import urllib.parse
from typing import List, Dict, Any
from .intake_agent import PatientProfile

logger = logging.getLogger("clinical_agent")

# ClinicalTrials.gov API v2 — may be blocked by Cloudflare on some networks.
# Fallback: use NCBI E-utilities to search PubMed Clinical Trials subset,
# then also query the public ClinicalTrials FHIR API as a second alternative.
HEADERS_BROWSER = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://clinicaltrials.gov/",
    "Connection": "keep-alive",
}


async def _query_clinicaltrials_gov(condition: str, location: str | None, client: httpx.AsyncClient) -> List[Dict]:
    """Primary: Query ClinicalTrials.gov API v2 directly."""
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    params: Dict[str, Any] = {
        "query.cond": condition,
        "filter.overallStatus": "RECRUITING",
        "pageSize": 5,
        "format": "json",
    }
    if location:
        params["query.locn"] = location

    response = await client.get(base_url, params=params, timeout=12.0)
    response.raise_for_status()
    data = response.json()
    return data.get("studies", [])


async def _query_pubmed_clinical_trials(condition: str, location: str | None, client: httpx.AsyncClient) -> List[Dict]:
    """
    Fallback: Search NCBI PubMed for published clinical trial records matching the condition.
    Returns synthetic 'trial' dicts shaped to match the main response format.
    """
    # Build a PubMed query targeting the clinicaltrials filter
    query_parts = [f"{condition}[Title/Abstract]", "Clinical Trial[pt]"]
    if location:
        query_parts.append(f"{location}[Affiliation]")
    query = " AND ".join(query_parts)

    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    search_resp = await client.get(search_url, params={
        "db": "pubmed", "term": query, "retmode": "json", "retmax": 5
    }, timeout=10.0)
    search_resp.raise_for_status()
    id_list = search_resp.json().get("esearchresult", {}).get("idlist", [])

    if not id_list:
        return []

    sum_resp = await client.get(summary_url, params={
        "db": "pubmed", "id": ",".join(id_list), "retmode": "json"
    }, timeout=10.0)
    sum_resp.raise_for_status()
    results = sum_resp.json().get("result", {})

    trials = []
    for pmid in id_list:
        rec = results.get(pmid, {})
        if not rec:
            continue
        title = rec.get("title", "Untitled Clinical Trial")
        authors = rec.get("authors", [])
        sponsor = authors[0].get("name", "Unknown Sponsor") if authors else "Unknown Sponsor"
        journal = rec.get("source", "")
        pubdate = rec.get("pubdate", "")

        trials.append({
            "nct_id": f"PMID:{pmid}",
            "title": title,
            "phase": "See Publication",
            "sponsor": f"{sponsor} ({journal})",
            "summary": (
                f"Published clinical trial retrieved from PubMed ({pubdate}). "
                f"Study relates to {condition}. "
                "Follow the PubMed link for eligibility details."
            ),
            "age_range": "See publication",
            "gender_requirement": "ALL",
            "locations": [location] if location else [],
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })

    return trials


def _parse_clinicaltrials_study(study: Dict) -> Dict:
    """Extract structured fields from a ClinicalTrials.gov v2 study object."""
    protocol = study.get("protocolSection", {})

    ident = protocol.get("identificationModule", {})
    nct_id = ident.get("nctId", "Unknown")
    brief_title = ident.get("briefTitle", "No Title Available")

    desc = protocol.get("descriptionModule", {})
    summary = desc.get("briefSummary", "No summary provided.")

    design = protocol.get("designModule", {})
    phases = design.get("phases", [])
    phase = ", ".join(phases) if phases else "Phase not specified"

    eligibility = protocol.get("eligibilityModule", {})
    min_age = eligibility.get("minimumAge", "Any age")
    max_age = eligibility.get("maximumAge", "Any age")
    gender_req = eligibility.get("sex", "ALL")

    sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
    sponsor = sponsor_module.get("leadSponsor", {}).get("name", "Unknown Sponsor")

    contacts_locations = protocol.get("contactsLocationsModule", {})
    raw_locations = contacts_locations.get("locations", [])
    location_list = []
    for loc in raw_locations[:3]:
        parts = [p for p in [
            loc.get("facility", ""),
            loc.get("city", ""),
            loc.get("state", ""),
            loc.get("country", ""),
        ] if p]
        if parts:
            location_list.append(", ".join(parts))

    return {
        "nct_id": nct_id,
        "title": brief_title,
        "phase": phase,
        "sponsor": sponsor,
        "summary": summary[:500],
        "age_range": f"{min_age} - {max_age}",
        "gender_requirement": gender_req,
        "locations": location_list,
        "url": f"https://clinicaltrials.gov/study/{nct_id}",
    }


async def match_clinical_trials(profile: PatientProfile) -> List[Dict[str, Any]]:
    """
    Queries ClinicalTrials.gov for active recruiting trials matching the patient profile.
    Falls back to PubMed published clinical trial records if the primary API is blocked.
    """
    condition = profile.condition.strip()
    location = profile.location

    async with httpx.AsyncClient(headers=HEADERS_BROWSER, follow_redirects=True) as client:

        # --- Attempt 1: ClinicalTrials.gov API v2 direct ---
        try:
            studies = await _query_clinicaltrials_gov(condition, location, client)
            if studies:
                logger.info(f"ClinicalTrials.gov returned {len(studies)} studies.")
                return [_parse_clinicaltrials_study(s) for s in studies]

            # Try without location filter as well
            if location:
                studies = await _query_clinicaltrials_gov(condition, None, client)
                if studies:
                    logger.info(f"ClinicalTrials.gov (no-location fallback) returned {len(studies)} studies.")
                    return [_parse_clinicaltrials_study(s) for s in studies]

        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.warning(f"ClinicalTrials.gov primary query failed ({e}). Switching to PubMed fallback.")

        # --- Attempt 2: PubMed Clinical Trials fallback ---
        try:
            logger.info("Using PubMed clinical trials fallback.")
            trials = await _query_pubmed_clinical_trials(condition, location, client)
            if trials:
                logger.info(f"PubMed fallback returned {len(trials)} trial records.")
            return trials
        except Exception as e:
            logger.exception(f"PubMed fallback also failed: {e}")
            return []
