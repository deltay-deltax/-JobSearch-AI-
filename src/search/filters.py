"""Stage 6: Metadata Filtering, Personalization, and Multi-Mode Retrieval (Hybrid, BM25, Vector).

Extends the search engine to support:
1. Mode switching: 'hybrid' (RRF), 'bm25' (keyword only), 'vector' (semantic only)
2. Detailed, transparent 'Why was it listed?' explanations for every single result
3. User preference boosting (skills, location)
4. Hard SQL metadata pre/post filters
"""

from typing import List, Optional, Set, Dict, Any, Literal
from dataclasses import dataclass, field

from src.ingestion.schema import JobPosting
from src.search.bm25_search import BM25Index, BM25SearchResult
from src.search.hybrid_search import HybridSearchEngine, HybridSearchResult
from src.search.db import VectorDB, DBSearchResult
from src.config import DEFAULT_TOP_K


@dataclass
class UserPreferences:
    """Captures user preferences for soft score boosting."""
    preferred_skills: List[str] = field(default_factory=list)
    preferred_location: Optional[str] = None
    experience_level: Optional[str] = None
    employment_types: Set[str] = field(default_factory=set)
    skill_boost_weight: float = 0.004
    location_boost: float = 0.002

    def normalize_skills(self) -> List[str]:
        return [s.strip().lower() for s in self.preferred_skills]


@dataclass
class FilterSpec:
    """Hard filter constraints."""
    location_contains: Optional[str] = None
    experience_level: Optional[str] = None
    employment_type: Optional[str] = None


@dataclass
class PersonalizedResult:
    """Final result enriched with personalization and diagnostic explanations."""
    job: JobPosting
    rrf_score: float
    boost: float
    final_score: float
    rank: int
    bm25_rank: Optional[int] = None
    bm25_score: float = 0.0
    vector_rank: Optional[int] = None
    vector_score: float = 0.0
    matched_skills: List[str] = field(default_factory=list)
    matched_terms: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    mode: str = "hybrid"
    explanation: str = ""

    def why_matched(self) -> str:
        """Returns the in-depth, transparent explanation of why this job appeared."""
        if self.explanation:
            return self.explanation

        reasons = []
        if self.mode == "bm25":
            if self.matched_terms:
                reasons.append(f"Exact keyword match on: '{', '.join(self.matched_terms)}'")
            reasons.append(f"BM25 frequency score: {self.bm25_score:.2f}")
        elif self.mode == "vector":
            reasons.append(f"Semantic cosine similarity: {self.vector_score:.4f}")
            reasons.append("Retrieved via pgvector 384-dim HNSW neural embedding space")
        else:
            # Hybrid
            if self.bm25_rank and self.vector_rank:
                reasons.append(
                    f"Strong consensus: Ranked #{self.bm25_rank} in BM25 (Score: {self.bm25_score:.2f}) "
                    f"and #{self.vector_rank} in pgvector (Cosine: {self.vector_score:.2f})"
                )
                if self.matched_terms:
                    reasons.append(f"Keywords matched: {', '.join(self.matched_terms)}")
            elif self.vector_rank:
                reasons.append(f"Semantic match: Ranked #{self.vector_rank} in pgvector (Cosine: {self.vector_score:.2f})")
            elif self.bm25_rank:
                reasons.append(f"Keyword match: Ranked #{self.bm25_rank} in BM25 (Score: {self.bm25_score:.2f})")

        if self.matched_skills:
            reasons.append(f"Preferred skills matched: {', '.join(self.matched_skills)}")

        if self.boost > 0:
            reasons.append(f"Preference boost: +{self.boost:.4f}")

        return " | ".join(reasons) if reasons else "Retrieved by search engine"


class PersonalizedSearchEngine:
    """Multi-mode search engine with personalization and explanation generation."""

    def __init__(self, **hybrid_kwargs):
        self.hybrid = HybridSearchEngine(**hybrid_kwargs)

    def fit(self, jobs: List[JobPosting]) -> "PersonalizedSearchEngine":
        self.hybrid.fit(jobs)
        return self

    def _compute_preference_boost(self, job: JobPosting, prefs: UserPreferences) -> float:
        boost = 0.0
        normalized_pref_skills = set(prefs.normalize_skills())
        normalized_job_skills = set(s.lower() for s in job.skills)

        # Skill overlap boost
        overlap = normalized_pref_skills & normalized_job_skills
        boost += len(overlap) * prefs.skill_boost_weight

        # Location boost
        if prefs.preferred_location:
            if prefs.preferred_location.lower() in job.location.lower():
                boost += prefs.location_boost
            if "remote" in job.location.lower():
                boost += prefs.location_boost * 0.5

        return boost

    def _compute_skill_overlap(self, job: JobPosting, prefs: UserPreferences) -> List[str]:
        normalized_pref = set(prefs.normalize_skills())
        normalized_job = set(s.lower() for s in job.skills)
        return sorted(normalized_pref & normalized_job)

    def _search_bm25_only(
        self,
        query: str,
        top_k: int,
        loc_filter: Optional[str],
        exp_filter: Optional[str],
        emp_filter: Optional[str],
        prefs: Optional[UserPreferences],
    ) -> List[PersonalizedResult]:
        """Executes BM25 keyword-only retrieval."""
        raw_results = self.hybrid.bm25_index.search(query, top_k=top_k * 3)

        # Apply metadata filters
        filtered: List[BM25SearchResult] = []
        for r in raw_results:
            if loc_filter and loc_filter.lower() not in r.job.location.lower():
                continue
            if exp_filter and r.job.experience_required != exp_filter:
                continue
            if emp_filter and r.job.employment_type.lower() != emp_filter.lower():
                continue
            filtered.append(r)

        results = []
        for rank, r in enumerate(filtered[:top_k], start=1):
            boost = self._compute_preference_boost(r.job, prefs) if prefs else 0.0
            matched_skills = self._compute_skill_overlap(r.job, prefs) if prefs else []
            
            terms_str = f"'{', '.join(r.matched_terms)}'" if r.matched_terms else "title/description"
            expl = (
                f"Keyword Match: Matched {terms_str} in inverted index. "
                f"BM25 Score: {r.score:.2f} (TF saturation + doc length normalization). "
                f"Rank #{rank} in keyword retrieval."
            )

            results.append(
                PersonalizedResult(
                    job=r.job,
                    rrf_score=r.score,
                    boost=boost,
                    final_score=r.score + boost,
                    rank=rank,
                    bm25_rank=rank,
                    bm25_score=r.score,
                    matched_skills=matched_skills,
                    matched_terms=r.matched_terms,
                    sources=["BM25"],
                    mode="bm25",
                    explanation=expl,
                )
            )
        return results

    def _search_vector_only(
        self,
        query: str,
        top_k: int,
        loc_filter: Optional[str],
        exp_filter: Optional[str],
        emp_filter: Optional[str],
        prefs: Optional[UserPreferences],
    ) -> List[PersonalizedResult]:
        """Executes Vector (pgvector)-only semantic retrieval."""
        query_vec = self.hybrid.vector_engine.encode(query, normalize=True)
        with VectorDB() as db:
            raw_results = db.search_semantic(
                query_embedding=query_vec,
                top_k=top_k * 2,
                location_filter=loc_filter,
                experience_filter=exp_filter,
                employment_type_filter=emp_filter,
            )

        # Quality guardrail: filter out out-of-domain noise (cosine < 0.22)
        valid_results = [r for r in raw_results if r.score >= 0.22]

        results = []
        for rank, r in enumerate(valid_results[:top_k], start=1):
            boost = self._compute_preference_boost(r.job, prefs) if prefs else 0.0
            matched_skills = self._compute_skill_overlap(r.job, prefs) if prefs else []

            sim_pct = int(r.score * 100)
            expl = (
                f"Semantic Match: {r.score:.4f} Cosine Similarity (~{sim_pct}% semantic intent alignment). "
                f"Retrieved from PostgreSQL pgvector 384-dim HNSW graph index based on natural language conceptual meaning."
            )

            results.append(
                PersonalizedResult(
                    job=r.job,
                    rrf_score=r.score,
                    boost=boost,
                    final_score=r.score + boost,
                    rank=rank,
                    vector_rank=rank,
                    vector_score=r.score,
                    matched_skills=matched_skills,
                    matched_terms=[],
                    sources=["Vector"],
                    mode="vector",
                    explanation=expl,
                )
            )
        return results

    def _search_hybrid(
        self,
        query: str,
        top_k: int,
        loc_filter: Optional[str],
        exp_filter: Optional[str],
        emp_filter: Optional[str],
        prefs: Optional[UserPreferences],
        bm25_candidate_k: int,
        vector_candidate_k: int,
    ) -> List[PersonalizedResult]:
        """Executes Hybrid (BM25 + pgvector + RRF) retrieval with in-depth explanations."""
        hybrid_results = self.hybrid.search(
            query=query,
            top_k=top_k * 2,
            bm25_candidate_k=bm25_candidate_k,
            vector_candidate_k=vector_candidate_k,
            location_filter=loc_filter,
            experience_filter=exp_filter,
            employment_type_filter=emp_filter,
        )

        # Match terms lookup from BM25 index for explanation detail
        bm25_raw = {r.job.id: r.matched_terms for r in self.hybrid.bm25_index.search(query, top_k=50)}

        personalized = []
        for hr in hybrid_results:
            boost = self._compute_preference_boost(hr.job, prefs) if prefs else 0.0
            matched_skills = self._compute_skill_overlap(hr.job, prefs) if prefs else []
            matched_terms = bm25_raw.get(hr.job.id, [])

            # Construct comprehensive explanation
            if hr.bm25_rank and hr.vector_rank:
                expl = (
                    f"Hybrid Consensus (Dual-Engine Winner): Ranked #{hr.vector_rank} in pgvector "
                    f"(Cosine: {hr.vector_score:.2f}) and #{hr.bm25_rank} in BM25 (Score: {hr.bm25_score:.2f}). "
                    f"Merged via RRF: 1/(60+{hr.bm25_rank}) + 1/(60+{hr.vector_rank}) = {hr.rrf_score:.4f}. "
                    f"Matched keywords: '{', '.join(matched_terms) if matched_terms else 'in description'}'."
                )
            elif hr.vector_rank:
                expl = (
                    f"Semantic Retrieval: Ranked #{hr.vector_rank} in pgvector (Cosine: {hr.vector_score:.2f}). "
                    f"Surfaced because conceptual meaning aligns with your query, even with zero exact keyword match."
                )
            elif hr.bm25_rank:
                terms_fmt = f"'{', '.join(matched_terms)}'" if matched_terms else "title keywords"
                expl = (
                    f"Exact Keyword Match: Ranked #{hr.bm25_rank} in BM25 (Score: {hr.bm25_score:.2f}) on {terms_fmt}."
                )
            else:
                expl = f"RRF Hybrid Score: {hr.rrf_score:.4f}."

            if matched_skills:
                expl += f" Matching candidate skills: {', '.join(matched_skills)}."

            personalized.append(
                PersonalizedResult(
                    job=hr.job,
                    rrf_score=hr.rrf_score,
                    boost=round(boost, 6),
                    final_score=round(hr.rrf_score + boost, 6),
                    rank=0,
                    bm25_rank=hr.bm25_rank,
                    bm25_score=hr.bm25_score,
                    vector_rank=hr.vector_rank,
                    vector_score=hr.vector_score,
                    matched_skills=matched_skills,
                    matched_terms=matched_terms,
                    sources=hr.sources,
                    mode="hybrid",
                    explanation=expl,
                )
            )

        personalized.sort(key=lambda x: x.final_score, reverse=True)
        for i, r in enumerate(personalized[:top_k], start=1):
            r.rank = i

        return personalized[:top_k]

    def search(
        self,
        query: str,
        prefs: Optional[UserPreferences] = None,
        filters: Optional[FilterSpec] = None,
        top_k: int = DEFAULT_TOP_K,
        mode: Literal["hybrid", "vector", "bm25"] = "hybrid",
        bm25_candidate_k: int = 50,
        vector_candidate_k: int = 50,
    ) -> List[PersonalizedResult]:
        """Main search entrypoint supporting hybrid, bm25, or vector modes."""
        if not query.strip():
            return []

        # Resolve filter parameters
        loc_filter = None
        exp_filter = None
        emp_filter = None

        if filters:
            loc_filter = filters.location_contains
            exp_filter = filters.experience_level
            emp_filter = filters.employment_type
        elif prefs:
            exp_filter = prefs.experience_level
            if prefs.employment_types and len(prefs.employment_types) == 1:
                emp_filter = next(iter(prefs.employment_types))

        if mode == "bm25":
            return self._search_bm25_only(query, top_k, loc_filter, exp_filter, emp_filter, prefs)
        elif mode == "vector":
            return self._search_vector_only(query, top_k, loc_filter, exp_filter, emp_filter, prefs)
        else:
            return self._search_hybrid(
                query, top_k, loc_filter, exp_filter, emp_filter, prefs,
                bm25_candidate_k, vector_candidate_k
            )
