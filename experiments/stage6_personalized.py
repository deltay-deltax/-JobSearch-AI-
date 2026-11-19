"""Stage 6 Interactive Demo: Personalized Search with Preference Boosting.

Shows the difference between:
1. Plain hybrid search (no preferences)
2. Personalized search with hard filters
3. Personalized search with skill boosting
4. The 'why_matched()' explanation for each result
"""

from src.ingestion.loader import load_raw_jobs
from src.ingestion.schema import JobPosting
from src.search.filters import PersonalizedSearchEngine, UserPreferences, FilterSpec
from src.config import DEFAULT_PROCESSED_JOBS_PATH


def run_demo():
    print("=" * 65)
    print("STAGE 6 — PERSONALIZED SEARCH WITH METADATA FILTERING")
    print("=" * 65)

    raw = load_raw_jobs(DEFAULT_PROCESSED_JOBS_PATH)
    jobs = [JobPosting(**item) for item in raw]

    engine = PersonalizedSearchEngine()
    engine.fit(jobs)

    # ── Scenario 1: Fresher looking for Python internships in Bangalore ──
    print("\n--- Scenario 1: Fresher, Python + FastAPI, Bangalore Internship ---")
    prefs = UserPreferences(
        preferred_skills=["Python", "FastAPI", "Docker"],
        preferred_location="Bangalore",
        experience_level="Fresher",
        employment_types={"Internship"},
        skill_boost_weight=0.004,
        location_boost=0.002,
    )
    filters = FilterSpec(
        experience_level="Fresher",
        employment_type="Internship",
    )
    results = engine.search(
        "backend engineering intern Python FastAPI",
        prefs=prefs,
        filters=filters,
        top_k=5,
    )
    for r in results:
        print(f"\n  Rank {r.rank}: {r.job.title} @ {r.job.company} ({r.job.location})")
        print(f"    RRF: {r.rrf_score:.5f}  +  Boost: {r.boost:.5f}  =  Final: {r.final_score:.5f}")
        print(f"    Matched Skills: {r.matched_skills or 'none'}")
        print(f"    Why: {r.why_matched()}")

    # ── Scenario 2: Mid-level full stack dev, React + Python, Remote ──
    print("\n\n--- Scenario 2: 1-3 yrs experience, Full Stack, Remote preferred ---")
    prefs2 = UserPreferences(
        preferred_skills=["React", "Python", "Node.js", "FastAPI"],
        preferred_location="Remote",
        experience_level="1-3 years",
        employment_types={"Full-time"},
        skill_boost_weight=0.004,
        location_boost=0.003,
    )
    filters2 = FilterSpec(
        experience_level="1-3 years",
        employment_type="Full-time",
    )
    results2 = engine.search(
        "full stack engineer React Python APIs",
        prefs=prefs2,
        filters=filters2,
        top_k=5,
    )
    for r in results2:
        print(f"\n  Rank {r.rank}: {r.job.title} @ {r.job.company} ({r.job.location})")
        print(f"    RRF: {r.rrf_score:.5f}  +  Boost: {r.boost:.5f}  =  Final: {r.final_score:.5f}")
        print(f"    Matched Skills: {r.matched_skills or 'none'}")
        print(f"    Why: {r.why_matched()}")

    # ── Scenario 3: Show soft boost effect — no hard location filter ──
    print("\n\n--- Scenario 3: Soft Boost Demo (Bangalore preferred but NOT filtered) ---")
    prefs3 = UserPreferences(
        preferred_skills=["Python"],
        preferred_location="Bangalore",   # soft preference only
        skill_boost_weight=0.004,
        location_boost=0.004,
    )
    results3 = engine.search("Python developer", prefs=prefs3, top_k=5)
    for r in results3:
        loc_note = "⬆ preferred location" if "Bangalore" in r.job.location else ""
        print(f"  Rank {r.rank}: [{r.final_score:.5f}] {r.job.title} @ {r.job.company} ({r.job.location}) {loc_note}")

    print("\n" + "=" * 65)


if __name__ == "__main__":
    run_demo()
