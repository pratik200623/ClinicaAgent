import asyncio, sys
sys.path.insert(0, '.')
from backend.agents.intake_agent import PatientProfile
from backend.agents.clinical_agent import match_clinical_trials

async def test():
    profile = PatientProfile(
        condition="Non-Small Cell Lung Cancer",
        age=58,
        gender="male",
        location="California",
        variants=["EGFR T790M"]
    )
    trials = await match_clinical_trials(profile)
    print(f"Found {len(trials)} trials")
    for t in trials[:3]:
        nct = t["nct_id"]
        title = t["title"][:70]
        phase = t["phase"]
        print(f"  [{nct}] {title} ({phase})")

asyncio.run(test())
