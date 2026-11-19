"""Information Retrieval Evaluation Metrics for JobSearch AI.

Implements standard IR benchmarks:
1. Precision@K: Proportion of top-k retrieved items that are relevant.
2. Recall@K:    Proportion of all known relevant items that were retrieved in top-k.
3. MRR:         Mean Reciprocal Rank — how high the first relevant document is.
4. NDCG@K:      Normalized Discounted Cumulative Gain — rewards placing highly
                relevant items at higher ranks with logarithmic position decay.
"""

from typing import List, Set, Dict, Union
import math


def precision_at_k(retrieved_ids: List[str], relevant_ids: Union[Set[str], List[str]], k: int) -> float:
    """Calculates Precision@K.
    
    Formula:
        Precision@K = (# of relevant items in top-K) / K
        
    Args:
        retrieved_ids: Ordered list of document IDs returned by search.
        relevant_ids: Set or list of known ground-truth relevant document IDs.
        k: Cutoff rank.
        
    Returns:
        Float value in range [0.0, 1.0].
    """
    if k <= 0:
        return 0.0
    top_k = retrieved_ids[:k]
    rel_set = set(relevant_ids)
    hits = sum(1 for item in top_k if item in rel_set)
    return hits / k


def recall_at_k(retrieved_ids: List[str], relevant_ids: Union[Set[str], List[str]], k: int) -> float:
    """Calculates Recall@K.
    
    Formula:
        Recall@K = (# of relevant items in top-K) / (Total # of relevant items)
        
    Args:
        retrieved_ids: Ordered list of document IDs returned by search.
        relevant_ids: Set or list of known ground-truth relevant document IDs.
        k: Cutoff rank.
        
    Returns:
        Float value in range [0.0, 1.0].
    """
    rel_set = set(relevant_ids)
    if not rel_set:
        return 0.0
    top_k = retrieved_ids[:k]
    hits = sum(1 for item in top_k if item in rel_set)
    return hits / len(rel_set)


def reciprocal_rank(retrieved_ids: List[str], relevant_ids: Union[Set[str], List[str]]) -> float:
    """Calculates Reciprocal Rank (RR).
    
    Formula:
        RR = 1 / rank_of_first_relevant_item
        (0.0 if no relevant item is found in retrieved list)
    """
    rel_set = set(relevant_ids)
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in rel_set:
            return 1.0 / rank
    return 0.0


def dcg_at_k(retrieved_ids: List[str], relevance_map: Dict[str, float], k: int) -> float:
    """Calculates Discounted Cumulative Gain at K.
    
    Formula:
        DCG@K = sum_{i=1}^K rel_i / log2(i + 1)
    """
    dcg = 0.0
    for i, doc_id in enumerate(retrieved_ids[:k], start=1):
        rel = relevance_map.get(doc_id, 0.0)
        dcg += rel / math.log2(i + 1)
    return dcg


def ndcg_at_k(
    retrieved_ids: List[str],
    relevant_ids: Union[Set[str], List[str], Dict[str, float]],
    k: int
) -> float:
    """Calculates Normalized Discounted Cumulative Gain at K (NDCG@K).
    
    Formula:
        NDCG@K = DCG@K / IDCG@K
        
    Where IDCG@K is the Ideal DCG obtained by sorting all relevant documents
    by relevance in descending order.
    
    Args:
        retrieved_ids: Ordered list of document IDs returned by search.
        relevant_ids: Set/list of binary relevant IDs or dict mapping doc_id -> graded relevance score.
        k: Cutoff rank.
        
    Returns:
        Float value in range [0.0, 1.0].
    """
    if k <= 0:
        return 0.0

    if isinstance(relevant_ids, (set, list)):
        rel_map = {doc_id: 1.0 for doc_id in relevant_ids}
    else:
        rel_map = dict(relevant_ids)

    if not rel_map:
        return 0.0

    # Actual DCG@K
    actual_dcg = dcg_at_k(retrieved_ids, rel_map, k)

    # Ideal DCG@K (sort all known relevant items by score descending)
    ideal_scores = sorted(rel_map.values(), reverse=True)
    idcg = sum(score / math.log2(i + 1) for i, score in enumerate(ideal_scores[:k], start=1))

    if idcg == 0.0:
        return 0.0

    return actual_dcg / idcg
