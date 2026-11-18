"""Interactive Toy Experiment for Stage 3: Embeddings & Semantic Search.

Demonstrates:
1. Converting text into 384-dimensional dense vectors
2. Vector magnitude (L2 norm) and dot products
3. Calculating Cosine Similarity manually vs vectorized
4. Semantic understanding: Recognizing that "server-side engineer" means "backend developer"
5. Solving BM25's failure: Matching "deep learning neural networks" to "AI/ML Engineer"
"""

import numpy as np
from src.search.vector_search import VectorSearchEngine, compute_cosine_similarity
from src.ingestion.schema import JobPosting


def run_toy_experiment():
    print("=" * 65)
    print("STAGE 3: STEP-BY-STEP EMBEDDING & COSINE SIMILARITY TOY EXPERIMENT")
    print("=" * 65)

    engine = VectorSearchEngine()

    print("\n[Step 1] Loading Pretrained Transformer Model...")
    print(f"Model: {engine.model_name}")

    phrase_1 = "Python backend developer"
    phrase_2 = "Server-side engineer working with Python"
    phrase_3 = "Frontend React UI designer"
    phrase_4 = "Executive sales account manager"

    # Encode phrases
    print("\n[Step 2] Generating Dense Vector Embeddings...")
    vec_1 = engine.encode(phrase_1, normalize=True)
    vec_2 = engine.encode(phrase_2, normalize=True)
    vec_3 = engine.encode(phrase_3, normalize=True)
    vec_4 = engine.encode(phrase_4, normalize=True)

    print(f"Vector Dimensionality: {vec_1.shape[0]} floating-point numbers")
    print(f"Sample of first 5 dimensions of '{phrase_1}':")
    print(f"  {vec_1[:5]}")
    print(f"L2 Norm (length) of vector: {np.linalg.norm(vec_1):.4f} (normalized to unit length)")

    # Compute Cosine Similarities
    print("\n[Step 3] Computing Semantic Cosine Similarities:")
    sim_1_2 = compute_cosine_similarity(vec_1, vec_2)
    sim_1_3 = compute_cosine_similarity(vec_1, vec_3)
    sim_1_4 = compute_cosine_similarity(vec_1, vec_4)

    print(f"  Similarity('{phrase_1}', '{phrase_2}'): {sim_1_2:.4f}")
    print("    -> High! Even with different words ('backend' vs 'server-side'), vectors cluster together.")
    print(f"  Similarity('{phrase_1}', '{phrase_3}'): {sim_1_3:.4f}")
    print("    -> Moderate. Both are software development roles, but distinct domains.")
    print(f"  Similarity('{phrase_1}', '{phrase_4}'): {sim_1_4:.4f}")
    print("    -> Low. Unrelated industry domains.")

    # Step 4: Demonstrating the fix for BM25's failure in Stage 2
    print("\n[Step 4] The Vocabulary Mismatch Solution:")
    print("In Stage 2, BM25 scored 0 for 'deep learning neural networks' against AI/ML jobs.")
    
    ai_job_desc = "AI / ML Engineer building semantic retrieval pipelines with PyTorch and Hugging Face."
    query = "deep learning neural networks"
    
    vec_job = engine.encode(ai_job_desc, normalize=True)
    vec_q = engine.encode(query, normalize=True)
    sim_ai = compute_cosine_similarity(vec_job, vec_q)

    print(f"  Query: '{query}'")
    print(f"  Job:   '{ai_job_desc}'")
    print(f"  Cosine Similarity: {sim_ai:.4f}")
    print("  -> Success! Vector embeddings capture conceptual meaning without needing exact word matches.")
    print("=" * 65)


if __name__ == "__main__":
    run_toy_experiment()
