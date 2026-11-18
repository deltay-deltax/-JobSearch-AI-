"""Stage 4 pipeline runner: Index all jobs into PostgreSQL + pgvector.

Runs the complete ingestion pipeline:
  1. Load 80 cleaned job records from disk
  2. Load pre-computed embeddings from cache (or recompute)
  3. Create the jobs table + HNSW index in PostgreSQL
  4. Upsert all job records + their embedding vectors
  5. Run a live semantic similarity search to verify everything works
"""

from src.ingestion.loader import load_raw_jobs
from src.ingestion.schema import JobPosting
from src.search.vector_search import VectorSearchEngine
from src.search.db import VectorDB
from src.config import DEFAULT_PROCESSED_JOBS_PATH


def run_stage4_pipeline(drop_existing: bool = False):
    print("=" * 60)
    print("STAGE 4: PostgreSQL + pgvector Indexing Pipeline")
    print("=" * 60)

    # Step 1: Load cleaned jobs from disk
    print("\n[1/4] Loading cleaned job records...")
    raw = load_raw_jobs(DEFAULT_PROCESSED_JOBS_PATH)
    jobs = [JobPosting(**item) for item in raw]
    print(f"      Loaded {len(jobs)} job records.")

    # Step 2: Generate (or load cached) embeddings
    print("\n[2/4] Loading embeddings (from cache if available)...")
    engine = VectorSearchEngine()
    engine.fit(jobs)
    embeddings = engine.embeddings
    print(f"      Embeddings shape: {embeddings.shape}  (jobs × dimensions)")

    # Step 3: Create schema
    print("\n[3/4] Creating database schema...")
    with VectorDB() as db:
        db.create_schema(drop_existing=drop_existing)
        print("      ✓ Table 'jobs' ready.")
        print("      ✓ HNSW index (cosine) created.")

        # Step 4: Ingest jobs + vectors
        print("\n[4/4] Ingesting job records into PostgreSQL...")
        n = db.ingest_jobs(jobs, embeddings)
        total = db.count_jobs()
        print(f"      ✓ Upserted {n} records. Total in DB: {total}")

        # Step 5: Verification — live semantic search
        print("\n--- Live Semantic Search Verification ---")
        queries = [
            ("Python backend internship Bangalore fresher", None, None, None),
            ("deep learning neural networks transformer AI", None, None, None),
            ("React frontend engineer", None, None, "Full-time"),
        ]

        for query, loc, exp, emp_type in queries:
            query_vec = engine.encode(query, normalize=True)
            results = db.search_semantic(
                query_embedding=query_vec,
                top_k=3,
                location_filter=loc,
                experience_filter=exp,
                employment_type_filter=emp_type,
            )
            print(f"\nQuery: '{query}'")
            for r in results:
                print(f"  Rank {r.rank}: [{r.score:.4f}] {r.job.title} @ {r.job.company} ({r.job.location})")

    print("\n✓ Stage 4 complete — PostgreSQL + pgvector is fully operational.")
    print("=" * 60)


if __name__ == "__main__":
    run_stage4_pipeline(drop_existing=True)
