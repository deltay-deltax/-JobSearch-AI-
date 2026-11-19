"""Search Engine Comparative Evaluation Benchmark Harness.

Compares three retrieval strategies against 20 benchmark queries:
1. BM25 Only (Traditional Keyword Search)
2. Dense Vector Only (pgvector / SentenceTransformers)
3. Hybrid Search (BM25 + Vector + Reciprocal Rank Fusion)

Measures:
- Precision@5, Precision@10
- Recall@5, Recall@10
- NDCG@5, NDCG@10
- Mean Reciprocal Rank (MRR)
"""

from typing import List, Dict, Any
from pathlib import Path
import json

from src.ingestion.loader import load_raw_jobs
from src.ingestion.schema import JobPosting
from src.search.bm25_search import BM25Index
from src.search.hybrid_search import HybridSearchEngine
from src.search.db import VectorDB
from src.evaluation.metrics import precision_at_k, recall_at_k, ndcg_at_k, reciprocal_rank
from src.config import DEFAULT_PROCESSED_JOBS_PATH, EVALUATION_DATA_DIR


class SearchBenchmark:
    """Evaluates and compares BM25, Vector Search, and Hybrid RRF."""

    def __init__(self, queries_path: Path = EVALUATION_DATA_DIR / "sample_test_queries.json"):
        with open(queries_path, "r", encoding="utf-8") as f:
            self.test_cases: List[Dict[str, Any]] = json.load(f)

        raw_jobs = load_raw_jobs(DEFAULT_PROCESSED_JOBS_PATH)
        self.jobs = [JobPosting(**item) for item in raw_jobs]

        # Initialize engines
        self.bm25 = BM25Index().fit(self.jobs)
        self.hybrid = HybridSearchEngine().fit(self.jobs)

    def run_bm25(self, query: str, top_k: int = 10) -> List[str]:
        results = self.bm25.search(query, top_k=top_k)
        return [r.job.id for r in results]

    def run_vector(self, query: str, top_k: int = 10) -> List[str]:
        query_vec = self.hybrid.vector_engine.encode(query, normalize=True)
        with VectorDB() as db:
            results = db.search_semantic(query_vec, top_k=top_k)
        return [r.job.id for r in results]

    def run_hybrid(self, query: str, top_k: int = 10) -> List[str]:
        results = self.hybrid.search(query, top_k=top_k)
        return [r.job.id for r in results]

    def evaluate_engine(self, engine_name: str, runner_func) -> Dict[str, float]:
        """Runs all test queries against the given engine and computes mean metrics."""
        p5_list, r5_list, ndcg5_list = [], [], []
        p10_list, r10_list, ndcg10_list = [], [], []
        mrr_list = []

        for tc in self.test_cases:
            query = tc["query"]
            relevant = set(tc["relevant_job_ids"])

            retrieved = runner_func(query, top_k=10)

            # Metrics @ 5
            p5_list.append(precision_at_k(retrieved, relevant, k=5))
            r5_list.append(recall_at_k(retrieved, relevant, k=5))
            ndcg5_list.append(ndcg_at_k(retrieved, relevant, k=5))

            # Metrics @ 10
            p10_list.append(precision_at_k(retrieved, relevant, k=10))
            r10_list.append(recall_at_k(retrieved, relevant, k=10))
            ndcg10_list.append(ndcg_at_k(retrieved, relevant, k=10))

            # MRR
            mrr_list.append(reciprocal_rank(retrieved, relevant))

        n = len(self.test_cases)
        return {
            "engine": engine_name,
            "Precision@5": sum(p5_list) / n,
            "Recall@5": sum(r5_list) / n,
            "NDCG@5": sum(ndcg5_list) / n,
            "Precision@10": sum(p10_list) / n,
            "Recall@10": sum(r10_list) / n,
            "NDCG@10": sum(ndcg10_list) / n,
            "MRR": sum(mrr_list) / n,
        }

    def run_full_benchmark(self) -> List[Dict[str, Any]]:
        """Executes the comparative evaluation across all 3 systems."""
        print(f"Running benchmark on {len(self.test_cases)} queries across {len(self.jobs)} indexed jobs...\n")

        bm25_metrics = self.evaluate_engine("BM25 Only", self.run_bm25)
        vec_metrics = self.evaluate_engine("Vector (pgvector) Only", self.run_vector)
        hybrid_metrics = self.evaluate_engine("Hybrid Search (RRF)", self.run_hybrid)

        return [bm25_metrics, vec_metrics, hybrid_metrics]

    def print_comparison_table(self, results: List[Dict[str, Any]]):
        """Displays a clean ASCII comparison table."""
        headers = ["Search Strategy", "P@5", "R@5", "NDCG@5", "P@10", "R@10", "NDCG@10", "MRR"]
        print("=" * 86)
        print("STAGE 7: SEARCH QUALITY BENCHMARK EVALUATION RESULTS")
        print("=" * 86)
        print(f"{headers[0]:<25} {headers[1]:<8} {headers[2]:<8} {headers[3]:<10} {headers[4]:<8} {headers[5]:<8} {headers[6]:<10} {headers[7]:<8}")
        print("-" * 86)

        for res in results:
            print(
                f"{res['engine']:<25} "
                f"{res['Precision@5']:<8.4f} "
                f"{res['Recall@5']:<8.4f} "
                f"{res['NDCG@5']:<10.4f} "
                f"{res['Precision@10']:<8.4f} "
                f"{res['Recall@10']:<8.4f} "
                f"{res['NDCG@10']:<10.4f} "
                f"{res['MRR']:<8.4f}"
            )
        print("=" * 86)


if __name__ == "__main__":
    benchmark = SearchBenchmark()
    res = benchmark.run_full_benchmark()
    benchmark.print_comparison_table(res)
