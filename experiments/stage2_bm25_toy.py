"""Interactive Toy Example for Stage 2: BM25 Mechanics.

Demonstrates:
1. Tokenization and stop-word filtering
2. Term Frequency (TF) calculation
3. Inverse Document Frequency (IDF) calculation
4. Length normalization penalty
5. Why TF saturation prevents keyword stuffing
"""

import math
from collections import Counter
from src.search.bm25_search import BM25Index, tokenize
from src.ingestion.schema import JobPosting


def run_toy_example():
    print("=" * 60)
    print("STAGE 2: STEP-BY-STEP BM25 TOY EXPERIMENT")
    print("=" * 60)

    # 3 Toy Job Postings to inspect the math manually
    jobs = [
        JobPosting(
            id="job_toy_1",
            title="Python Backend Developer",
            company="Startup Alpha",
            description="We build fast microservices with Python, FastAPI, and PostgreSQL.",
            skills=["Python", "FastAPI"],
            location="Bangalore",
        ),
        JobPosting(
            id="job_toy_2",
            title="Frontend React Engineer",
            company="DesignCo",
            description="Building beautiful interactive user interfaces with React, TypeScript, and CSS.",
            skills=["React", "TypeScript"],
            location="Remote",
        ),
        JobPosting(
            id="job_toy_3",
            title="Data Scientist",
            company="BigData Inc",
            description="Analyze data using Python, Pandas, and machine learning models in Python environment.",
            skills=["Python", "Pandas"],
            location="Bangalore",
        ),
    ]

    index = BM25Index(k1=1.5, b=0.75).fit(jobs)

    print(f"\nCorpus Size (N): {index.corpus_size}")
    print(f"Average Document Length (avgdl): {index.avg_doc_len:.2f} tokens")
    print("\nDocument Frequencies & IDFs:")
    for term in ["python", "fastapi", "react", "bangalore"]:
        df = index.doc_frequencies.get(term, 0)
        idf = index.idf.get(term, 0.0)
        print(f"  - Term '{term}': DF={df}/{index.corpus_size}, IDF={idf:.4f}")

    query = "Python FastAPI Bangalore"
    print(f"\nSearch Query: '{query}'")
    results = index.search(query, top_k=3)

    print("\nRanked Results:")
    for res in results:
        print(f"  Rank {res.rank}: [{res.score:.4f}] {res.job.title} at {res.job.company}")
        print(f"          Matched Terms: {res.matched_terms}")

    # Step-by-step score explanation for the top result
    print("\nScore Breakdown for Rank 1:")
    explanation = index.explain_score(query, 0)
    for term_info in explanation["terms"]:
        print(f"  Term: '{term_info['term']}'")
        print(f"    TF={term_info['tf']}, DF={term_info['df']}, IDF={term_info['idf']:.4f}")
        print(f"    Contribution to score: {term_info['term_contribution']:.4f}")
    print(f"  Total BM25 Score: {explanation['total_score']}")
    print("=" * 60)


if __name__ == "__main__":
    run_toy_example()
