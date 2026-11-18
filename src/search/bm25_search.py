"""BM25 (Best Matching 25) Keyword Search Engine for JobSearch AI.

This module implements an inverted index and Okapi BM25 scoring algorithm from scratch.
Provides transparent relevance scoring, term frequency saturation, document length
normalization, and score explanations for educational clarity.
"""

from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
import math
import re
from collections import Counter

from src.ingestion.schema import JobPosting


# Standard English stop words to avoid skewing relevance on filler words
DEFAULT_STOP_WORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "cannot", "could", "did", "do",
    "does", "doing", "down", "during", "each", "few", "for", "from", "further",
    "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "isn't", "it", "its",
    "itself", "just", "me", "more", "most", "my", "myself", "no", "nor", "not",
    "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
    "ourselves", "out", "over", "own", "same", "she", "should", "so", "some",
    "such", "than", "that", "the", "their", "theirs", "them", "themselves",
    "then", "there", "these", "they", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "we", "were", "what", "when", "where",
    "which", "while", "who", "whom", "why", "with", "would", "you", "your",
    "yours", "yourself", "yourselves"
}


def tokenize(text: str, remove_stopwords: bool = True) -> List[str]:
    """Tokenizes text into normalized lowercase word tokens.
    
    Handles tech tokens like 'c++', 'c#', 'node.js', and 'fastapi'.
    
    Args:
        text: Input string.
        remove_stopwords: Whether to filter out standard English stop words.
        
    Returns:
        List of cleaned token strings.
    """
    if not text:
        return []
    
    # Preserve technical terms before general splitting
    lowered = text.lower()
    
    # Extract alphanumeric words and special tech identifiers
    raw_tokens = re.findall(r"[a-z0-9+#]+(?:\.[a-z0-9]+)*", lowered)
    
    if remove_stopwords:
        return [t for t in raw_tokens if t not in DEFAULT_STOP_WORDS and len(t) > 1]
    return [t for t in raw_tokens if len(t) > 1]


@dataclass
class BM25SearchResult:
    """Represents a scored and ranked job search result."""
    job: JobPosting
    score: float
    rank: int
    matched_terms: List[str]


class BM25Index:
    """Okapi BM25 Information Retrieval Index with an Inverted Index.
    
    BM25 Formula:
        Score(D, Q) = sum_{q in Q} IDF(q) * (f(q, D) * (k1 + 1)) / (f(q, D) + k1 * (1 - b + b * (|D| / avgdl)))
        
    Hyperparameters:
        k1 (float): Term frequency saturation parameter (typically 1.2 to 2.0).
                    Higher k1 gives more weight to repeated occurrences of a term.
        b (float): Document length normalization parameter (typically 0.75).
                   b=1 completely penalizes long documents; b=0 disables length penalty.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

        # Corpus-level statistics
        self.jobs: List[JobPosting] = []
        self.corpus_size: int = 0
        self.avg_doc_len: float = 0.0
        self.doc_lengths: List[int] = []

        # Term statistics
        self.doc_frequencies: Dict[str, int] = {}  # n(q): number of docs containing term
        self.idf: Dict[str, float] = {}             # IDF per term
        
        # Inverted Index: mapping token -> list of (doc_index, term_frequency)
        # Allows sub-millisecond retrieval by only inspecting docs that contain query terms.
        self.inverted_index: Dict[str, List[Tuple[int, int]]] = {}

    def fit(self, jobs: List[JobPosting]) -> "BM25Index":
        """Builds the inverted index and precalculates corpus statistics."""
        self.jobs = list(jobs)
        self.corpus_size = len(jobs)
        self.doc_lengths = []
        self.doc_frequencies = {}
        self.inverted_index = {}

        if self.corpus_size == 0:
            self.avg_doc_len = 0.0
            return self

        total_length = 0

        # Step 1: Tokenize all documents and build inverted index
        for doc_idx, job in enumerate(self.jobs):
            tokens = tokenize(job.to_searchable_text())
            doc_len = len(tokens)
            self.doc_lengths.append(doc_len)
            total_length += doc_len

            # Calculate Term Frequency (TF) for this doc
            counts = Counter(tokens)
            for term, count in counts.items():
                self.doc_frequencies[term] = self.doc_frequencies.get(term, 0) + 1
                if term not in self.inverted_index:
                    self.inverted_index[term] = []
                self.inverted_index[term].append((doc_idx, count))

        self.avg_doc_len = total_length / self.corpus_size if self.corpus_size > 0 else 0.0

        # Step 2: Precalculate IDF for all terms
        # Okapi BM25 IDF formula with 1.0 floor smoothing to prevent negative IDF for frequent words
        for term, df in self.doc_frequencies.items():
            # Standard Lucene / Robertson-Spärck-Jones IDF:
            # IDF = ln(1 + (N - n + 0.5) / (n + 0.5))
            numerator = self.corpus_size - df + 0.5
            denominator = df + 0.5
            self.idf[term] = math.log(1.0 + (numerator / denominator))

        return self

    def score_document(self, query_terms: List[str], doc_idx: int, tf_map: Dict[str, int]) -> float:
        """Calculates BM25 score for a specific document given query terms."""
        doc_len = self.doc_lengths[doc_idx]
        score = 0.0
        
        # Length normalization factor: (1 - b + b * (doc_len / avgdl))
        len_norm = 1.0 - self.b + self.b * (doc_len / self.avg_doc_len) if self.avg_doc_len > 0 else 1.0

        for term in query_terms:
            tf = tf_map.get(term, 0)
            if tf == 0:
                continue
            
            term_idf = self.idf.get(term, 0.0)
            
            # Saturated TF: (tf * (k1 + 1)) / (tf + k1 * len_norm)
            numerator = tf * (self.k1 + 1.0)
            denominator = tf + self.k1 * len_norm
            
            score += term_idf * (numerator / denominator)

        return score

    def search(self, query: str, top_k: int = 10) -> List[BM25SearchResult]:
        """Executes keyword search against the inverted index.
        
        Args:
            query: Natural language or keyword query.
            top_k: Number of highest-ranking results to return.
            
        Returns:
            List of BM25SearchResult sorted descending by score.
        """
        query_terms = tokenize(query)
        if not query_terms or self.corpus_size == 0:
            return []

        # Find matching documents and accumulate their scores
        # We use an accumulator map: doc_idx -> (score, matched_terms_set)
        candidate_scores: Dict[int, float] = {}
        candidate_matches: Dict[int, List[str]] = {}

        for term in query_terms:
            postings = self.inverted_index.get(term)
            if not postings:
                continue

            term_idf = self.idf.get(term, 0.0)

            for doc_idx, tf in postings:
                doc_len = self.doc_lengths[doc_idx]
                len_norm = 1.0 - self.b + self.b * (doc_len / self.avg_doc_len) if self.avg_doc_len > 0 else 1.0
                
                # BM25 term contribution
                term_score = term_idf * (tf * (self.k1 + 1.0)) / (tf + self.k1 * len_norm)

                candidate_scores[doc_idx] = candidate_scores.get(doc_idx, 0.0) + term_score
                
                if doc_idx not in candidate_matches:
                    candidate_matches[doc_idx] = []
                if term not in candidate_matches[doc_idx]:
                    candidate_matches[doc_idx].append(term)

        # Sort candidate documents by score descending
        ranked_docs = sorted(candidate_scores.items(), key=lambda item: item[1], reverse=True)

        results: List[BM25SearchResult] = []
        for rank, (doc_idx, score) in enumerate(ranked_docs[:top_k], start=1):
            results.append(
                BM25SearchResult(
                    job=self.jobs[doc_idx],
                    score=round(score, 4),
                    rank=rank,
                    matched_terms=candidate_matches.get(doc_idx, []),
                )
            )

        return results

    def explain_score(self, query: str, doc_idx: int) -> Dict[str, any]:
        """Provides a detailed mathematical breakdown of how a score was calculated.
        
        Crucial for learning, debugging, and interview demonstrations.
        """
        if doc_idx >= len(self.jobs) or doc_idx < 0:
            raise IndexError("Document index out of bounds.")

        query_terms = tokenize(query)
        doc_len = self.doc_lengths[doc_idx]
        len_norm = 1.0 - self.b + self.b * (doc_len / self.avg_doc_len) if self.avg_doc_len > 0 else 1.0

        tokens = tokenize(self.jobs[doc_idx].to_searchable_text())
        tf_map = Counter(tokens)

        breakdown = {
            "job_id": self.jobs[doc_idx].id,
            "title": self.jobs[doc_idx].title,
            "doc_length": doc_len,
            "avg_corpus_length": round(self.avg_doc_len, 2),
            "length_normalization_factor": round(len_norm, 4),
            "terms": []
        }

        total_score = 0.0
        for term in query_terms:
            tf = tf_map.get(term, 0)
            term_idf = self.idf.get(term, 0.0)
            term_score = 0.0
            if tf > 0:
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * len_norm
                term_score = term_idf * (numerator / denominator)
                total_score += term_score

            breakdown["terms"].append({
                "term": term,
                "tf": tf,
                "df": self.doc_frequencies.get(term, 0),
                "idf": round(term_idf, 4),
                "term_contribution": round(term_score, 4),
            })

        breakdown["total_score"] = round(total_score, 4)
        return breakdown
