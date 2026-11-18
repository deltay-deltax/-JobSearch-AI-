"""Dense Vector Semantic Search Engine for JobSearch AI.

This module implements vector embedding generation, vector caching, and
cosine similarity retrieval using Sentence Transformers and NumPy.
Demonstrates the transition from discrete keyword matching (BM25) to continuous
semantic embedding space.
"""

from typing import List, Optional, Tuple, Union
from dataclasses import dataclass
from pathlib import Path
import numpy as np

from src.ingestion.schema import JobPosting
from src.config import DEFAULT_EMBEDDING_MODEL, PROCESSED_DATA_DIR


@dataclass
class VectorSearchResult:
    """Represents a semantically retrieved and ranked job posting."""
    job: JobPosting
    score: float  # Cosine similarity score [-1.0, 1.0]
    rank: int


def compute_cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Calculates the cosine similarity between two 1D numerical vectors.
    
    Formula:
        Cosine Similarity(A, B) = (A . B) / (||A||_2 * ||B||_2)
        
    Geometrically measures the cosine of the angle between two vectors in n-dimensional space.
    If both vectors are already L2-normalized (unit length ||A|| = 1), this reduces
    strictly to the dot product (A . B).
    """
    dot_product = float(np.dot(vec_a, vec_b))
    norm_a = float(np.linalg.norm(vec_a))
    norm_b = float(np.linalg.norm(vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


class VectorSearchEngine:
    """In-Memory Dense Vector Search Engine using Sentence Transformers and NumPy.
    
    Attributes:
        model_name: Hugging Face model identifier (e.g. 'all-MiniLM-L6-v2', 384 dimensions).
        model: Lazy-loaded SentenceTransformer instance.
        embeddings: 2D NumPy array of shape (N, D) where N is job count and D is vector dimensionality.
        jobs: List of indexed JobPosting objects.
        cache_file: Filepath where computed embeddings are persisted to avoid re-encoding.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        cache_file: Optional[Path] = None,
    ):
        self.model_name = model_name
        self.cache_file = cache_file or (PROCESSED_DATA_DIR / f"embeddings_{model_name.replace('/', '_')}.npy")
        self._model = None

        self.jobs: List[JobPosting] = []
        self.embeddings: Optional[np.ndarray] = None  # Shape: (N, D)
        self.vector_dim: int = 0

    @property
    def model(self):
        """Lazy load the transformer model only when needed."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        """Converts raw text or batch of texts into numerical dense vector embeddings.
        
        Args:
            texts: Single string or list of text strings.
            normalize: If True, L2-normalizes vectors so ||v|| = 1.
            
        Returns:
            NumPy array of float32 embeddings.
        """
        is_single = isinstance(texts, str)
        input_list = [texts] if is_single else texts
        
        # SentenceTransformers encode returns a numpy ndarray
        embeddings = self.model.encode(
            input_list,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
            show_progress_bar=False,
        )
        return embeddings[0] if is_single else embeddings

    def fit(self, jobs: List[JobPosting], force_recompute: bool = False) -> "VectorSearchEngine":
        """Indexes job descriptions into continuous vector embedding space.
        
        If a cache file exists and record count matches, loads pre-computed vectors
        in milliseconds instead of running deep learning model inference.
        """
        self.jobs = list(jobs)
        n_jobs = len(self.jobs)

        if n_jobs == 0:
            self.embeddings = None
            self.vector_dim = 0
            return self

        # Check for persisted cache
        if not force_recompute and self.cache_file.exists():
            try:
                cached = np.load(self.cache_file)
                if cached.shape[0] == n_jobs:
                    self.embeddings = cached
                    self.vector_dim = cached.shape[1]
                    return self
            except Exception:
                pass  # Fallback to computing if cache read fails

        # Generate embeddings for all jobs using their composite searchable text
        texts_to_embed = [job.to_searchable_text() for job in self.jobs]
        self.embeddings = self.encode(texts_to_embed, normalize=True)
        self.vector_dim = self.embeddings.shape[1]

        # Persist to disk for rapid subsequent startups
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            np.save(self.cache_file, self.embeddings)
        except Exception:
            pass

        return self

    def search(self, query: str, top_k: int = 10) -> List[VectorSearchResult]:
        """Performs semantic similarity search against the indexed job listings.
        
        Args:
            query: Freeform natural language query.
            top_k: Number of most similar results to return.
            
        Returns:
            List of VectorSearchResult ordered from highest to lowest cosine similarity.
        """
        if self.embeddings is None or len(self.jobs) == 0 or not query.strip():
            return []

        # 1. Encode user query into embedding vector (normalized to unit length)
        query_vec = self.encode(query, normalize=True)  # Shape: (D,)

        # 2. Vectorized batch cosine similarity
        # Since both query_vec and self.embeddings are L2-normalized,
        # Cosine Similarity is equivalent to the Matrix-Vector dot product:
        # scores = (N, D) @ (D,) -> (N,)
        scores = np.dot(self.embeddings, query_vec)

        # 3. Retrieve indices of top-k highest scores
        # np.argsort sorts in ascending order, so we reverse it with [::-1]
        top_indices = np.argsort(scores)[::-1][:top_k]

        results: List[VectorSearchResult] = []
        for rank, idx in enumerate(top_indices, start=1):
            results.append(
                VectorSearchResult(
                    job=self.jobs[idx],
                    score=round(float(scores[idx]), 4),
                    rank=rank,
                )
            )

        return results
