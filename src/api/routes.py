"""FastAPI Router implementing the search endpoints."""

import time
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from src.api.schemas import SearchRequest, SearchResponse, SearchResultItem, HealthResponse
from src.search.filters import PersonalizedSearchEngine, UserPreferences, FilterSpec
from src.search.db import VectorDB
from src.config import DEFAULT_EMBEDDING_MODEL

router = APIRouter(prefix="/api")

# Singleton search engine initialized in main.py lifespan
_search_engine: Optional[PersonalizedSearchEngine] = None


def set_engine(engine: PersonalizedSearchEngine):
    global _search_engine
    _search_engine = engine


def get_engine() -> PersonalizedSearchEngine:
    if _search_engine is None:
        raise HTTPException(status_code=503, detail="Search engine not yet initialized")
    return _search_engine


@router.get("/health", response_model=HealthResponse)
def health_check():
    """Checks database availability and indexing status."""
    pg_connected = False
    count = 0
    try:
        with VectorDB() as db:
            count = db.count_jobs()
            pg_connected = True
    except Exception:
        pg_connected = False

    return HealthResponse(
        status="healthy" if pg_connected else "degraded",
        total_jobs_indexed=count,
        postgres_connected=pg_connected,
        embedding_model=DEFAULT_EMBEDDING_MODEL,
    )


@router.post("/search", response_model=SearchResponse)
def search_jobs(req: SearchRequest, engine: PersonalizedSearchEngine = Depends(get_engine)):
    """Executes personalized hybrid, vector, or keyword search."""
    start_time = time.perf_counter()

    # User preferences for soft boosting
    prefs = UserPreferences(
        preferred_skills=req.preferred_skills or [],
        preferred_location=req.location,
        experience_level=req.experience,
        employment_types={req.employment_type} if req.employment_type else set(),
    )

    # Filter constraints
    filters = FilterSpec(
        location_contains=req.location,
        experience_level=req.experience,
        employment_type=req.employment_type,
    )

    results = engine.search(
        query=req.query,
        prefs=prefs if req.preferred_skills else None,
        filters=filters if (req.location or req.experience or req.employment_type) else None,
        top_k=req.top_k,
        mode=req.mode,
    )

    duration_ms = (time.perf_counter() - start_time) * 1000

    items = [
        SearchResultItem(
            job_id=r.job.id,
            title=r.job.title,
            company=r.job.company,
            location=r.job.location,
            experience=r.job.experience_required,
            employment_type=r.job.employment_type,
            salary=r.job.salary,
            skills=r.job.skills,
            score=round(r.final_score, 4),
            matched_skills=r.matched_skills,
            matched_terms=r.matched_terms,
            why_matched=r.why_matched(),
            sources=r.sources,
            mode=r.mode,
            bm25_score=round(r.bm25_score, 4),
            vector_score=round(r.vector_score, 4),
            bm25_rank=r.bm25_rank,
            vector_rank=r.vector_rank,
            application_url=r.job.application_url,
            description=r.job.description,
        )
        for r in results
    ]

    return SearchResponse(
        query=req.query,
        mode=req.mode,
        total_results=len(items),
        execution_time_ms=round(duration_ms, 2),
        results=items,
    )


@router.get("/jobs/{job_id}")
def get_job_by_id(job_id: str):
    """Retrieves full details for a single job listing."""
    with VectorDB() as db:
        job = db.get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
        return job.model_dump()
