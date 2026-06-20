import asyncio
import json
from typing import AsyncGenerator
from .intake_agent import parse_query
from .clinical_agent import match_clinical_trials
from .genomic_agent import interpret_genomic_variants
from .literature_agent import search_literature

async def run_orchestration_stream(query: str) -> AsyncGenerator[str, None]:
    """
    Runs the multi-agent orchestration workflow and yields JSON-formatted SSE events.
    Enables real-time tracking of agent actions on the frontend.
    """
    try:
        # Step 1: Intake Agent parses query
        yield json.dumps({
            "status": "processing",
            "agent": "IntakeAgent",
            "message": "Parsing patient natural language query into structured clinical parameters..."
        }) + "\n"
        await asyncio.sleep(0.8) # Small delay for visual pacing in UI
        
        profile = await parse_query(query)
        
        yield json.dumps({
            "status": "processing",
            "agent": "IntakeAgent",
            "message": f"Parameters extracted: Condition='{profile.condition}', Age={profile.age or 'N/A'}, Gender='{profile.gender or 'N/A'}', Location='{profile.location or 'N/A'}', Variants={profile.variants or 'None'}."
        }) + "\n"
        await asyncio.sleep(0.5)

        # Step 2: Trigger sub-agents in parallel
        yield json.dumps({
            "status": "processing",
            "agent": "CoordinatorAgent",
            "message": "Spawning Genomic, Clinical Matcher, and Literature Synthesis Agents concurrently..."
        }) + "\n"
        await asyncio.sleep(0.5)

        # Create tasks
        genomic_task = interpret_genomic_variants(profile)
        clinical_task = match_clinical_trials(profile)
        literature_task = search_literature(profile)

        # Yield starts for each agent
        yield json.dumps({
            "status": "processing",
            "agent": "GenomicAgent",
            "message": "Querying NCBI ClinVar database for genomic variants pathogenicity and records..."
        }) + "\n"
        
        yield json.dumps({
            "status": "processing",
            "agent": "ClinicalAgent",
            "message": f"Searching ClinicalTrials.gov for active & recruiting studies on '{profile.condition}'..."
        }) + "\n"
        
        yield json.dumps({
            "status": "processing",
            "agent": "LiteratureAgent",
            "message": f"Searching PubMed for recent clinical literature and treatment studies on '{profile.condition}'..."
        }) + "\n"

        # Execute concurrently
        genomic_results, clinical_results, literature_results = await asyncio.gather(
            genomic_task,
            clinical_task,
            literature_task
        )

        # Yield completions
        yield json.dumps({
            "status": "processing",
            "agent": "GenomicAgent",
            "message": f"Retrieved {len(genomic_results)} genomic variant profiles from ClinVar."
        }) + "\n"
        
        yield json.dumps({
            "status": "processing",
            "agent": "ClinicalAgent",
            "message": f"Matched {len(clinical_results)} active recruiting clinical trials."
        }) + "\n"
        
        yield json.dumps({
            "status": "processing",
            "agent": "LiteratureAgent",
            "message": f"Retrieved {len(literature_results)} relevant research articles from PubMed."
        }) + "\n"
        await asyncio.sleep(0.6)

        # Step 3: Synthesis
        yield json.dumps({
            "status": "processing",
            "agent": "CoordinatorAgent",
            "message": "Synthesizing data feeds and drafting final clinical summary report..."
        }) + "\n"
        await asyncio.sleep(0.8)

        # Create dynamic synthesis text
        synthesis = build_synthesis_report(profile, genomic_results, clinical_results, literature_results)

        # Package full result
        final_payload = {
            "profile": profile.model_dump(),
            "genomics": genomic_results,
            "clinical_trials": clinical_results,
            "literature": literature_results,
            "synthesis": synthesis
        }

        yield json.dumps({
            "status": "completed",
            "agent": "CoordinatorAgent",
            "message": "Synthesis complete. Dispatching results payload."
        }) + "\n"

        yield json.dumps({
            "status": "result",
            "data": final_payload
        }) + "\n"

    except Exception as e:
        yield json.dumps({
            "status": "error",
            "agent": "CoordinatorAgent",
            "message": f"An error occurred during multi-agent coordination: {str(e)}"
        }) + "\n"

def build_synthesis_report(profile, genomics, trials, literature) -> str:
    """
    Generates a structured medical synthesis statement summarizing all the agents' findings.
    """
    cond = profile.condition
    age_str = f"{profile.age}-year-old" if profile.age else "patient"
    gen_str = profile.gender or ""
    loc_str = f" near {profile.location}" if profile.location else ""
    
    parts = [
        f"Clinical report synthesis for a {age_str} {gen_str} diagnosed with **{cond}**{loc_str}.",
    ]
    
    # Genomics section
    if genomics:
        g_details = []
        for g in genomics:
            if g.get("status") == "Found":
                g_details.append(f"*{g['variant']}* (Gene: {g['gene']}) classified in ClinVar as **{g['clinical_significance']}**")
            else:
                g_details.append(f"*{g['variant']}* (unknown significance / not cataloged in ClinVar)")
        parts.append(f"**Genomic Interpretation:** Identified {len(genomics)} variant(s): {'; '.join(g_details)}.")
    else:
        parts.append("**Genomic Interpretation:** No genetic variants or mutations were specified for this analysis.")
        
    # Trials section
    if trials:
        parts.append(f"**Clinical Trial Matching:** Matched **{len(trials)}** active and recruiting clinical trials. Key trials include phase-appropriate experimental protocols investigating targeted therapies for {cond}. Recommending review of eligibility criteria, particularly regarding genomic marker specifications.")
    else:
        parts.append("**Clinical Trial Matching:** No active recruiting trials were matched with the specified parameters. Consider widening geographical parameters or checking general registries.")
        
    # Literature section
    if literature:
        parts.append(f"**Evidence & Literature Synthesis:** Retrieved **{len(literature)}** relevant PubMed articles. These papers detail recent therapeutic advances, drug efficacy studies, and molecular targets for {cond}, providing robust peer-reviewed evidence to support clinical decision-making.")
    else:
        parts.append("**Evidence & Literature Synthesis:** No direct literature references were recovered for this specific cohort criteria. Recommending a broader keyword search in MEDLINE/PubMed.")
        
    # Recommendation summary
    parts.append("\n**Recommendations for Clinical Review:**\n1. Validate genomic variant findings with standard diagnostic-grade sequencing tests.\n2. Screen eligibility criteria for matched trials, noting any specific inclusion exclusions (e.g. prior lines of therapy, organ function).\n3. Consult with the principal investigator or clinical research coordinator of matched trials.")

    return "\n\n".join(parts)
