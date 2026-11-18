"""Stage 4: PostgreSQL + pgvector Database Layer for JobSearch AI.

This module handles:
1. Database connection management (connection pooling)
2. Schema creation — jobs table with a vector(384) embedding column
3. HNSW vector index for fast Approximate Nearest Neighbour (ANN) search
4. Ingesting cleaned JobPosting records + their embeddings into Postgres
5. Semantic vector similarity search using pgvector's <=> operator (cosine distance)
6. Exact keyword/metadata filter queries using standard SQL WHERE clauses

Architecture:
    VectorDB
    ├── connect()          → open psycopg2 connection
    ├── create_schema()    → CREATE TABLE + pgvector HNSW index
    ├── ingest_jobs()      → INSERT job records + embedding vectors
    ├── search_semantic()  → pgvector cosine similarity ANN search
    ├── search_by_id()     → fetch single job by id
    └── get_all_jobs()     → fetch all indexed jobs (for BM25 fitting)
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import json

import psycopg2
import psycopg2.extras
import numpy as np

from src.ingestion.schema import JobPosting
from src.config import (
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD,
    EMBEDDING_DIM
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class DBSearchResult:
    """Single result returned from a pgvector similarity search."""
    job: JobPosting
    score: float        # Cosine SIMILARITY (1 - cosine_distance)
    rank: int


# ---------------------------------------------------------------------------
# Database connection helper
# ---------------------------------------------------------------------------

def get_connection() -> psycopg2.extensions.connection:
    """Opens and returns a psycopg2 connection to the jobsearch_ai database.

    Why psycopg2?
        It is the most widely used PostgreSQL adapter for Python.
        It speaks the PostgreSQL binary protocol natively and handles
        type conversions between Python objects and Postgres types.
    """
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


# ---------------------------------------------------------------------------
# Core VectorDB class
# ---------------------------------------------------------------------------

class VectorDB:
    """PostgreSQL + pgvector database interface for scalable semantic job search.

    Key concepts used in this module:
    ─────────────────────────────────
    • vector(384):
        A native PostgreSQL column type added by pgvector.
        Stores a 384-dimensional float32 array in a compact binary format.

    • Cosine Distance (<=>):
        pgvector's cosine distance operator.
        cosine_distance(a, b) = 1 - cosine_similarity(a, b)
        Score range: [0, 2].  0 = identical, 2 = diametrically opposite.
        We convert to similarity: similarity = 1 - distance.

    • HNSW Index (Hierarchical Navigable Small World):
        An Approximate Nearest Neighbour (ANN) graph-based index.
        Trades a small accuracy margin for sub-millisecond search at scale
        (millions of vectors vs full sequential scan).
        Parameters:
            m          = number of bi-directional links per node (default 16)
            ef_construction = beam width during index build (default 64)
    """

    def __init__(self):
        self.conn: Optional[psycopg2.extensions.connection] = None

    def connect(self) -> "VectorDB":
        """Opens a database connection."""
        self.conn = get_connection()
        return self

    def close(self):
        """Closes the database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()

    def __enter__(self):
        return self.connect()

    def __exit__(self, *args):
        self.close()

    # -----------------------------------------------------------------------
    # Schema setup
    # -----------------------------------------------------------------------

    def create_schema(self, drop_existing: bool = False) -> None:
        """Creates the jobs table and HNSW vector index.

        Table design:
            id              TEXT PRIMARY KEY   — matches our JobPosting.id
            title           TEXT               — job title
            company         TEXT               — company name
            description     TEXT               — full cleaned description
            skills          JSONB              — list of normalized skills
            location        TEXT               — city / remote
            experience_req  TEXT               — bucketed experience level
            employment_type TEXT               — full-time / internship etc.
            salary          TEXT               — salary string (nullable)
            application_url TEXT               — link to apply (nullable)
            embedding       vector(384)        — dense float32 embedding
            created_at      TIMESTAMPTZ        — record insertion time

        Why JSONB for skills?
            skills is a variable-length list. JSONB lets us:
            (a) Store it natively without a skills join table.
            (b) Query individual skills with Postgres JSON operators later.
            (c) Return it as a Python list via json.loads() trivially.
        """
        with self.conn.cursor() as cur:
            if drop_existing:
                cur.execute("DROP TABLE IF EXISTS jobs CASCADE;")

            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS jobs (
                    id              TEXT PRIMARY KEY,
                    title           TEXT NOT NULL,
                    company         TEXT NOT NULL,
                    description     TEXT NOT NULL,
                    skills          JSONB NOT NULL DEFAULT '[]',
                    location        TEXT NOT NULL DEFAULT 'Remote',
                    experience_req  TEXT NOT NULL DEFAULT 'Not Specified',
                    employment_type TEXT NOT NULL DEFAULT 'Full-time',
                    salary          TEXT,
                    application_url TEXT,
                    embedding       vector({EMBEDDING_DIM}),
                    created_at      TIMESTAMPTZ DEFAULT NOW()
                );
            """)

            # HNSW index on the embedding column using cosine distance operator class
            # This enables pgvector to use the graph index during <=> queries
            cur.execute("""
                CREATE INDEX IF NOT EXISTS jobs_embedding_hnsw_idx
                ON jobs
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            """)

            # Standard B-Tree indexes for metadata filter acceleration (Stage 6)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs (location);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_exp ON jobs (experience_req);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_emp_type ON jobs (employment_type);")

        self.conn.commit()

    # -----------------------------------------------------------------------
    # Ingestion
    # -----------------------------------------------------------------------

    def ingest_jobs(self, jobs: List[JobPosting], embeddings: np.ndarray) -> int:
        """Inserts cleaned job records and their embedding vectors into Postgres.

        Uses INSERT ... ON CONFLICT DO UPDATE (UPSERT) so the pipeline is
        safely idempotent — running it twice doesn't create duplicate records.

        Args:
            jobs:       List of validated JobPosting objects.
            embeddings: 2D NumPy float32 array of shape (N, 384).

        Returns:
            Number of rows upserted.
        """
        assert len(jobs) == len(embeddings), (
            f"Mismatch: {len(jobs)} jobs vs {len(embeddings)} embeddings"
        )

        upsert_sql = """
            INSERT INTO jobs (
                id, title, company, description,
                skills, location, experience_req, employment_type,
                salary, application_url, embedding
            ) VALUES (
                %(id)s, %(title)s, %(company)s, %(description)s,
                %(skills)s, %(location)s, %(experience_req)s, %(employment_type)s,
                %(salary)s, %(application_url)s, %(embedding)s
            )
            ON CONFLICT (id) DO UPDATE SET
                title           = EXCLUDED.title,
                company         = EXCLUDED.company,
                description     = EXCLUDED.description,
                skills          = EXCLUDED.skills,
                location        = EXCLUDED.location,
                experience_req  = EXCLUDED.experience_req,
                employment_type = EXCLUDED.employment_type,
                salary          = EXCLUDED.salary,
                application_url = EXCLUDED.application_url,
                embedding       = EXCLUDED.embedding;
        """

        rows = []
        for job, emb in zip(jobs, embeddings):
            # pgvector expects the embedding as a Python list of floats
            emb_list = emb.tolist()
            rows.append({
                "id":              job.id,
                "title":           job.title,
                "company":         job.company,
                "description":     job.description,
                "skills":          json.dumps(job.skills),
                "location":        job.location,
                "experience_req":  job.experience_required,
                "employment_type": job.employment_type,
                "salary":          job.salary,
                "application_url": job.application_url,
                "embedding":       str(emb_list),   # pgvector accepts '[f1,f2,...]' string
            })

        with self.conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, upsert_sql, rows, page_size=100)

        self.conn.commit()
        return len(rows)

    # -----------------------------------------------------------------------
    # Semantic search
    # -----------------------------------------------------------------------

    def search_semantic(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        location_filter: Optional[str] = None,
        experience_filter: Optional[str] = None,
        employment_type_filter: Optional[str] = None,
    ) -> List[DBSearchResult]:
        """Finds the top-k semantically similar jobs using pgvector's HNSW index.

        How the query works:
            1. We pass the query embedding as a string '[f1,f2,...]'.
            2. pgvector's <=> operator computes COSINE DISTANCE between the
               query vector and every stored embedding.
            3. The HNSW index navigates the graph to find approximate nearest
               neighbours in sub-millisecond time — no full table scan needed.
            4. We ORDER BY cosine_distance ASC (smallest distance = most similar).
            5. We convert distance to similarity: similarity = 1 - distance.

        Optional SQL WHERE clauses are appended for metadata pre-filtering.
        Pre-filtering means we restrict the candidate set BEFORE the ANN search,
        which is more efficient but can reduce recall. Post-filtering (filter after
        retrieval) is safer for recall but wastes compute on irrelevant candidates.
        """
        query_vec_str = str(query_embedding.tolist())

        where_clauses = []
        params: Dict[str, Any] = {"query_vec": query_vec_str, "top_k": top_k}

        if location_filter:
            where_clauses.append("LOWER(location) LIKE LOWER(%(location)s)")
            params["location"] = f"%{location_filter}%"

        if experience_filter:
            where_clauses.append("experience_req = %(experience_req)s")
            params["experience_req"] = experience_filter

        if employment_type_filter:
            where_clauses.append("LOWER(employment_type) = LOWER(%(employment_type)s)")
            params["employment_type"] = employment_type_filter

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        sql = f"""
            SELECT
                id, title, company, description,
                skills, location, experience_req, employment_type,
                salary, application_url,
                (embedding <=> %(query_vec)s::vector) AS cosine_distance
            FROM jobs
            {where_sql}
            ORDER BY cosine_distance ASC
            LIMIT %(top_k)s;
        """

        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        results = []
        for rank, row in enumerate(rows, start=1):
            # psycopg2 auto-deserializes JSONB columns to Python objects
            skills = row["skills"] if isinstance(row["skills"], list) else json.loads(row["skills"])
            job = JobPosting(
                id=row["id"],
                title=row["title"],
                company=row["company"],
                description=row["description"],
                skills=skills,
                location=row["location"],
                experience_required=row["experience_req"],
                employment_type=row["employment_type"],
                salary=row["salary"],
                application_url=row["application_url"],
            )
            cosine_distance = float(row["cosine_distance"])
            similarity = round(1.0 - cosine_distance, 4)
            results.append(DBSearchResult(job=job, score=similarity, rank=rank))

        return results

    # -----------------------------------------------------------------------
    # Utility queries
    # -----------------------------------------------------------------------

    def get_job_by_id(self, job_id: str) -> Optional[JobPosting]:
        """Fetches a single job by its primary key."""
        sql = """
            SELECT id, title, company, description, skills,
                   location, experience_req, employment_type,
                   salary, application_url
            FROM jobs WHERE id = %s;
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (job_id,))
            row = cur.fetchone()

        if not row:
            return None

        return JobPosting(
            id=row["id"],
            title=row["title"],
            company=row["company"],
            description=row["description"],
            skills=row["skills"] if isinstance(row["skills"], list) else json.loads(row["skills"]),
            location=row["location"],
            experience_required=row["experience_req"],
            employment_type=row["employment_type"],
            salary=row["salary"],
            application_url=row["application_url"],
        )

    def get_all_jobs(self) -> List[JobPosting]:
        """Returns all indexed jobs — used to re-fit BM25 from the database."""
        sql = """
            SELECT id, title, company, description, skills,
                   location, experience_req, employment_type,
                   salary, application_url
            FROM jobs ORDER BY id;
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()

        return [
            JobPosting(
                id=r["id"],
                title=r["title"],
                company=r["company"],
                description=r["description"],
                skills=r["skills"] if isinstance(r["skills"], list) else json.loads(r["skills"]),
                location=r["location"],
                experience_required=r["experience_req"],
                employment_type=r["employment_type"],
                salary=r["salary"],
                application_url=r["application_url"],
            )
            for r in rows
        ]

    def count_jobs(self) -> int:
        """Returns count of indexed jobs."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM jobs;")
            return cur.fetchone()[0]
