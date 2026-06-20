import httpx
import logging
from typing import List, Dict, Any
from .intake_agent import PatientProfile

logger = logging.getLogger("literature_agent")

async def search_literature(profile: PatientProfile) -> List[Dict[str, Any]]:
    """
    Queries NCBI PubMed to retrieve relevant medical articles and publications.
    """
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    
    # Construct a search query (e.g. "EGFR T790M lung cancer treatment")
    search_terms = []
    if profile.variants:
        search_terms.append(profile.variants[0]) # Use primary variant
    
    search_terms.append(profile.condition)
    search_terms.append("treatment")
    
    query_str = " ".join(search_terms)
    
    search_params = {
        "db": "pubmed",
        "term": query_str,
        "retmode": "json",
        "retmax": 5
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            logger.info(f"Querying PubMed search: {search_params}")
            response = await client.get(search_url, params=search_params)
            
            if response.status_code != 200:
                logger.error(f"PubMed Search API returned status code {response.status_code}")
                return []
                
            search_data = response.json()
            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            
            if not id_list:
                logger.info("No articles found on PubMed.")
                return []
                
            # Fetch summary details
            ids_str = ",".join(id_list)
            summary_params = {
                "db": "pubmed",
                "id": ids_str,
                "retmode": "json"
            }
            
            logger.info(f"Querying PubMed summaries for IDs: {ids_str}")
            summary_response = await client.get(summary_url, params=summary_params)
            
            if summary_response.status_code != 200:
                logger.error(f"PubMed Summary API returned status code {summary_response.status_code}")
                return []
                
            summary_data = summary_response.json()
            results = summary_data.get("result", {})
            
            articles = []
            for pmid in id_list:
                article = results.get(pmid)
                if not article:
                    continue
                    
                title = article.get("title", "No Title")
                pubdate = article.get("pubdate", "Unknown Date")
                source = article.get("source", "Unknown Journal")
                
                # Format authors
                authors_list = article.get("authors", [])
                authors = ", ".join([a.get("name", "") for a in authors_list[:3]])
                if len(authors_list) > 3:
                    authors += " et al."
                if not authors:
                    authors = "Unknown Authors"
                    
                # Extract PMCID and DOI if available
                pmcid = None
                doi = None
                for articleid in article.get("articleids", []):
                    if articleid.get("idtype") == "pmcid":
                        pmcid = articleid.get("value")
                    elif articleid.get("idtype") == "doi":
                        doi = articleid.get("value")
                        
                articles.append({
                    "pmid": pmid,
                    "title": title,
                    "authors": authors,
                    "journal": source,
                    "date": pubdate,
                    "pmcid": pmcid,
                    "doi": doi,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                })
                
            return articles
            
    except Exception as e:
        logger.exception(f"Error querying PubMed: {e}")
        return []
