"""Stage 5 Interactive Toy: RRF Math Demonstration.

Manually walks through 3 toy documents to show EXACTLY
how RRF merges two ranked lists step by step.
No database needed — pure Python math.
"""

from src.search.hybrid_search import HybridSearchEngine
from src.ingestion.schema import JobPosting
from src.ingestion.loader import load_raw_jobs
from src.config import DEFAULT_PROCESSED_JOBS_PATH


# ─── PART 1: Manual step-by-step RRF Math ────────────────────────────────

def manual_rrf_demo():
    print("=" * 65)
    print("STAGE 5 — MANUAL RRF CALCULATION (k=60)")
    print("=" * 65)

    k = 60

    # Imagine BM25 returned this ranked list:
    bm25_ranks = {
        "job_001": 1,  # "Backend Python Intern"
        "job_002": 2,  # "Junior Python Developer"
        "job_003": 3,  # "AI ML Engineer"
    }

    # And vector search returned this different ranked list:
    vector_ranks = {
        "job_003": 1,  # ANN thinks this is closest semantically
        "job_001": 2,
        "job_004": 3,  # New job that BM25 missed
    }

    all_jobs = set(bm25_ranks) | set(vector_ranks)
    rrf_scores = {}

    print(f"\n{'Job ID':<12} {'BM25 rank':<12} {'BM25 contrib':<16} "
          f"{'Vec rank':<12} {'Vec contrib':<14} {'RRF total'}")
    print("-" * 75)

    for job_id in sorted(all_jobs):
        b_rank = bm25_ranks.get(job_id)
        v_rank = vector_ranks.get(job_id)

        b_contrib = 1 / (k + b_rank) if b_rank else 0.0
        v_contrib = 1 / (k + v_rank) if v_rank else 0.0
        total = b_contrib + v_contrib
        rrf_scores[job_id] = total

        b_str = f"1/({k}+{b_rank})={b_contrib:.5f}" if b_rank else "not retrieved"
        v_str = f"1/({k}+{v_rank})={v_contrib:.5f}" if v_rank else "not retrieved"
        print(f"{job_id:<12} {str(b_rank):<12} {b_str:<16} {str(v_rank):<12} {v_str:<14} {total:.5f}")

    print("\nFinal RRF Ranking:")
    for rank, (jid, score) in enumerate(
        sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True), start=1
    ):
        print(f"  Rank {rank}: {jid}  →  RRF score = {score:.5f}")

    print("""
Key insight:
  job_001 → BM25 rank 1 AND vector rank 2 → highest combined score (wins)
  job_003 → BM25 rank 3 AND vector rank 1 → strong combined score
  job_004 → Only in vector list (rank 3)  → partial score only
  job_002 → Only in BM25 list (rank 2)    → partial score only
""")


# ─── PART 2: Live Hybrid Search on 80 Real Jobs ──────────────────────────

def live_hybrid_search():
    print("=" * 65)
    print("STAGE 5 — LIVE HYBRID SEARCH ON 80 REAL JOBS")
    print("=" * 65)

    raw = load_raw_jobs(DEFAULT_PROCESSED_JOBS_PATH)
    jobs = [JobPosting(**item) for item in raw]

    engine = HybridSearchEngine()
    engine.fit(jobs)

    test_queries = [
        {
            "query": "I am a fresher looking for backend engineering internships in Bangalore involving Python and FastAPI",
            "filters": {},
        },
        {
            "query": "deep learning neural networks transformer AI",
            "filters": {},
        },
        {
            "query": "Python backend developer",
            "filters": {"employment_type_filter": "Full-time", "experience_filter": "1-3 years"},
        },
    ]

    for item in test_queries:
        q = item["query"]
        filters = item["filters"]
        print(f"\nQuery: '{q}'")
        if filters:
            print(f"Filters: {filters}")
        print("-" * 60)

        results = engine.search(q, top_k=5, **filters)

        for r in results:
            bm25_info = f"BM25 rank {r.bm25_rank}" if r.bm25_rank else "BM25: —"
            vec_info  = f"Vec rank {r.vector_rank}"  if r.vector_rank  else "Vec: —"
            print(f"  Rank {r.rank}: [{r.rrf_score:.5f}] {r.job.title} @ {r.job.company} ({r.job.location})")
            print(f"           Sources: {r.sources}   |   {bm25_info}   |   {vec_info}")

    print("\n" + "=" * 65)


if __name__ == "__main__":
    manual_rrf_demo()
    live_hybrid_search()
