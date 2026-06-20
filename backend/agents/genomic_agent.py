import httpx
import logging
import asyncio
from typing import List, Dict, Any
from .intake_agent import PatientProfile

logger = logging.getLogger("genomic_agent")

async def fetch_variant_details(variant: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    """
    Queries ClinVar via NCBI E-utilities to get clinical significance and details for a single variant.
    """
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    
    # 1. Search ClinVar for the variant term
    search_params = {
        "db": "clinvar",
        "term": variant,
        "retmode": "json",
        "retmax": 3
    }
    
    try:
        response = await client.get(search_url, params=search_params)
        if response.status_code != 200:
            return {"variant": variant, "status": "Error", "message": f"Search returned status {response.status_code}"}
            
        search_data = response.json()
        id_list = search_data.get("esearchresult", {}).get("idlist", [])
        
        if not id_list:
            # Fallback search - just search as general term
            return {
                "variant": variant,
                "status": "Not Found in ClinVar",
                "clinical_significance": "Unknown / Not classified in ClinVar",
                "details": f"No direct matches found for variant: '{variant}'. It may be a rare variant or require clinical sequencing interpretation."
            }
            
        # 2. Fetch summary details for the IDs found
        ids_str = ",".join(id_list)
        summary_params = {
            "db": "clinvar",
            "id": ids_str,
            "retmode": "json"
        }
        
        summary_response = await client.get(summary_url, params=summary_params)
        if summary_response.status_code != 200:
            return {"variant": variant, "status": "Error", "message": f"Summary details returned status {summary_response.status_code}"}
            
        summary_data = summary_response.json()
        results = summary_data.get("result", {})
        
        variant_records = []
        for uid in id_list:
            record = results.get(uid)
            if not record:
                continue
                
            title = record.get("title", f"Variant {uid}")
            
            # Extract clinical significance description
            clin_sig = "Unknown"
            clin_sig_desc = record.get("clinical_significance", {})
            if isinstance(clin_sig_desc, dict):
                clin_sig = clin_sig_desc.get("description", "Unknown")
            elif isinstance(clin_sig_desc, str):
                clin_sig = clin_sig_desc
                
            # Extract associated gene
            genes = record.get("genes", [])
            gene_symbol = genes[0].get("symbol", "Unknown") if genes else "Unknown"
            
            # Extract chromosomal locations
            variation_locs = []
            variation_set = record.get("variation_set", [])
            for var in variation_set:
                for loc in var.get("variation_loc", []):
                    assembly = loc.get("assembly_name", "")
                    chrom = loc.get("chr", "")
                    start = loc.get("start", "")
                    stop = loc.get("stop", "")
                    if assembly and chrom:
                        variation_locs.append(f"{assembly} Chr{chrom}:{start}-{stop}")
            
            variant_records.append({
                "clinvar_id": uid,
                "title": title,
                "gene": gene_symbol,
                "locations": variation_locs,
                "clinical_significance": clin_sig,
                "url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{uid}/"
            })
            
        if variant_records:
            # Return the first match or merge them
            main_rec = variant_records[0]
            return {
                "variant": variant,
                "status": "Found",
                "title": main_rec["title"],
                "clinical_significance": main_rec["clinical_significance"],
                "gene": main_rec["gene"],
                "locations": main_rec["locations"],
                "clinvar_id": main_rec["clinvar_id"],
                "url": main_rec["url"]
            }
            
        return {"variant": variant, "status": "Not Found"}
        
    except Exception as e:
        logger.exception(f"Exception fetching variant details for {variant}: {e}")
        return {"variant": variant, "status": "Error", "message": str(e)}

async def interpret_genomic_variants(profile: PatientProfile) -> List[Dict[str, Any]]:
    """
    Orchestrates the lookup of all genetic variants found in the profile.
    """
    if not profile.variants:
        logger.info("No genetic variants to interpret in patient profile.")
        return []
        
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [fetch_variant_details(var, client) for var in profile.variants]
        results = await asyncio.gather(*tasks)
        return results
