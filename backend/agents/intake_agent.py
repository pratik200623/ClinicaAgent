import re
from pydantic import BaseModel, Field
from typing import List, Optional

class PatientProfile(BaseModel):
    condition: str = Field(..., description="The medical condition or disease")
    age: Optional[int] = Field(None, description="Patient's age in years")
    gender: Optional[str] = Field(None, description="Patient's gender (male, female, other)")
    location: Optional[str] = Field(None, description="Geographical location or region")
    variants: List[str] = Field(default_factory=list, description="List of genomic variants/mutations")

async def parse_query(query: str) -> PatientProfile:
    """
    Parses a raw natural language patient query into a structured PatientProfile.
    Uses regex pattern matching to extract age, gender, location, and genetic mutations.
    """
    # 1. Extract Age
    age = None
    age_patterns = [
        r"\b(\d{1,2})\s*-?\s*year\s*-?\s*old\b",
        r"\bage\s*(\d{1,2})\b",
        r"\b(\d{1,2})\s*yo\b",
        r"\b(\d{1,2})\s*years?\s*old\b"
    ]
    for pattern in age_patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            age = int(match.group(1))
            break

    # 2. Extract Gender
    gender = None
    if re.search(r"\bfemale\b|\bwoman\b|\bgirl\b|\bshe\b", query, re.IGNORECASE):
        gender = "female"
    elif re.search(r"\bmale\b|\bman\b|\bboy\b|\bhe\b", query, re.IGNORECASE):
        gender = "male"

    # 3. Extract Genetic Mutations (e.g., EGFR T790M, BRCA1, KRAS G12D, BRAF V600E)
    variants = []
    # Match standard mutation patterns: Gene name followed by mutation code (e.g., EGFR T790M, KRAS G12D, BRAF V600E)
    variant_pattern = r"\b(EGFR|BRCA1|BRCA2|KRAS|ALK|BRAF|PIK3CA|TP53|HER2|IDH1|IDH2|MET|RET|ROS1)\s+([A-Z]\d+[A-Z\d]*)\b"
    for match in re.finditer(variant_pattern, query, re.IGNORECASE):
        gene = match.group(1).upper()
        mutation = match.group(2).upper()
        variants.append(f"{gene} {mutation}")

    # Also capture bare gene mentions if they are described as mutated/mutations (e.g., BRCA1 mutation)
    bare_genes = re.findall(r"\b(BRCA1|BRCA2|EGFR|KRAS|ALK|BRAF)\s+(?:mutation|mutated|positive)\b", query, re.IGNORECASE)
    for gene in bare_genes:
        gene_upper = gene.upper()
        if not any(gene_upper in v for v in variants):
            variants.append(gene_upper)

    # 4. Extract Location
    location = None
    # Look for patterns like "in California", "near New York", "around London"
    location_patterns = [
        r"\bin\s+([A-Za-z\s]+?)(?:\s+and\s+|\s+with\s+|\s+having\s+|\s+looking\s+|\.|\,|$)",
        r"\bnear\s+([A-Za-z\s]+?)(?:\s+and\s+|\s+with\s+|\s+having\s+|\s+looking\s+|\.|\,|$)",
        r"\baround\s+([A-Za-z\s]+?)(?:\s+and\s+|\s+with\s+|\s+having\s+|\s+looking\s+|\.|\,|$)"
    ]
    for pattern in location_patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            loc = match.group(1).strip()
            # Exclude only generic stopwords, NOT real location names
            if loc.lower() not in ["a", "the", "my", "our", "detail", "detail page"]:
                location = loc
                break
    
    # Fallback default locations if we see them explicitly
    if not location:
        for state in ["California", "New York", "Texas", "Florida", "Illinois", "Washington", "Boston", "Houston"]:
            if re.search(rf"\b{state}\b", query, re.IGNORECASE):
                location = state
                break

    # 5. Extract Condition
    condition = "Cancer"  # default fallback
    # Let's search for standard medical conditions in the text
    conditions_db = [
        "non-small cell lung cancer", "nsclc", "small cell lung cancer", "lung cancer",
        "breast cancer", "triple negative breast cancer", "her2 positive breast cancer",
        "prostate cancer", "melanoma", "ovarian cancer", "colon cancer", "colorectal cancer",
        "pancreatic cancer", "leukemia", "lymphoma", "glioblastoma", "glioma",
        "alzheimer", "parkinson", "diabetes", "asthma", "arthritis",
        "cardiovascular disease", "heart disease", "hypertension", "crohn",
        "bladder cancer", "renal cell carcinoma", "kidney cancer", "liver cancer",
        "hepatocellular carcinoma", "thyroid cancer", "cervical cancer", "endometrial cancer"
    ]
    
    for cond in conditions_db:
        if re.search(rf"\b{re.escape(cond)}\b", query, re.IGNORECASE):
            condition = cond.upper() if len(cond) <= 5 else cond.title()
            break
    
    # If no condition from database matched, extract words before "with" or "diagnosed with"
    if condition == "Cancer":
        diagnosed_match = re.search(r"diagnosed with\s+([A-Za-z\s\-]+?)(?:\s+and\s+|\s+with\s+|\s+having\s+|\s+looking\s+|\d|\.|\,|$)", query, re.IGNORECASE)
        if diagnosed_match:
            condition = diagnosed_match.group(1).strip().title()
        else:
            # Try to grab the noun before "with"
            with_match = re.search(r"([A-Za-z\s\-]+?)\s+with\s+", query, re.IGNORECASE)
            if with_match:
                condition = with_match.group(1).strip().title()

    # Clean up condition (e.g. remove leading "a ", "an ", "stage iv ", etc.)
    condition = re.sub(r"^(a|an|the|stage\s+[i|v|x\d]+)\s+", "", condition, flags=re.IGNORECASE)
    
    return PatientProfile(
        condition=condition,
        age=age,
        gender=gender,
        location=location,
        variants=variants
    )
