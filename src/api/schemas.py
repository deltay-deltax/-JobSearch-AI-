"""Pydantic Request and Response Schemas for the FastAPI REST API."""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Payload for POST /api/search."""
    query: str = Field(min_length=1, description="Natural language search query")
    location: Optional[str] = Field(default=None, description="Location constraint or preference")
    experience: Optional[str] = Field(default=None, description="Fresher, 1-3 years, 3-5 years, 5+ years")
    employment_type: Optional[str] = Field(default=None, description="Full-time, Internship, Contract, etc.")
    preferred_skills: Optional[List[str]] = Field(default_factory=list, description="User skills for preference boosting")
    top_k: int = Field(default=10, ge=1, le=50, description="Number of results to return")
    mode: Literal["hybrid", "vector", "bm25"] = Field(default="hybrid", description="Retrieval strategy")


class SearchResultItem(BaseModel):
    """Individual job item returned in search response."""
    job_id: str
    title: str
    company: str
    location: str
    experience: str
    employment_type: str
    salary: Optional[str] = None
    skills: List[str]
    score: float
    matched_skills: List[str] = Field(default_factory=list)
    matched_terms: List[str] = Field(default_factory=list)
    why_matched: str
    sources: List[str] = Field(default_factory=list)
    mode: str = "hybrid"
    bm25_score: float = 0.0
    vector_score: float = 0.0
    bm25_rank: Optional[int] = None
    vector_rank: Optional[int] = None
    application_url: Optional[str] = None
    description: str


class SearchResponse(BaseModel):
    """Full response wrapper for POST /api/search."""
    query: str
    mode: str
    total_results: int
    execution_time_ms: float
    results: List[SearchResultItem]


class HealthResponse(BaseModel):
    """Response for GET /api/health."""
    status: str
    total_jobs_indexed: int
    postgres_connected: bool
    embedding_model: str
