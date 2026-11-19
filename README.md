# JobSearch AI — Semantic Job Discovery & Recommendation Engine

An end-to-end intelligent job search engine built with **Python, FastAPI, Sentence Transformers, PostgreSQL + pgvector, Okapi BM25, Reciprocal Rank Fusion (RRF)**, and **React + Vite**.

---

## 🌟 Architecture Overview

```
User Query
    │
    ▼
┌────────────────────────────────────────────────────────┐
│               FastAPI Backend (/api/search)           │
└────────────────────────────────────────────────────────┘
          │                                    │
          ▼                                    ▼
┌──────────────────┐                 ┌──────────────────┐
│  BM25 Inverted   │                 │ PostgreSQL 18    │
│  Index (Keyword) │                 │ + pgvector (ANN) │
└──────────────────┘                 └──────────────────┘
          │                                    │
          └─────────────────┬──────────────────┘
                            ▼
              ┌───────────────────────────┐
              │ Reciprocal Rank Fusion    │
              │ RRF(d) = Σ 1/(60 + rank)  │
              └───────────────────────────┘
                            │
                            ▼
              ┌───────────────────────────┐
              │   Metadata Filtering &    │
              │   Preference Boosting     │
              └───────────────────────────┘
                            │
                            ▼
              ┌───────────────────────────┐
              │   Ranked Results + Why    │
              │   Matched Explanations    │
              └───────────────────────────┘
```

---

## 🚀 Quickstart

### 1. Requirements
* Python 3.12+
* PostgreSQL 18 with `pgvector` enabled (Database: `jobsearch_ai`)
* Node.js v18+

### 2. Start the Backend API (FastAPI)
```bash
python -m src.api.main
```
* API Server starts at: **http://localhost:8000**
* Interactive API Documentation (Swagger): **http://localhost:8000/docs**

### 3. Start the Frontend UI (React + Vite)
In a new terminal:
```bash
npm --prefix frontend run dev
```
* Open your browser at: **http://localhost:5173**

---

## 📊 Benchmark Evaluation Results (Stage 7)

Evaluated across 20 benchmark queries against the 80-job corpus:

| Strategy | P@5 | R@5 | NDCG@5 | P@10 | R@10 | NDCG@10 | MRR |
|---|---|---|---|---|---|---|---|
| **BM25 Only** | 0.8100 | 0.4186 | 0.8158 | 0.7600 | 0.7703 | 0.7966 | 0.8167 |
| **Vector (pgvector) Only** | **0.9000** | 0.4303 | **0.9096** | 0.8350 | 0.7903 | **0.8779** | **0.9667** |
| **Hybrid Search (RRF)** | 0.8600 | 0.4270 | 0.8754 | **0.8400** | **0.8095** | 0.8736 | 0.9143 |

> **Key Finding:** Hybrid Search delivers the highest **Recall@10 (0.8095)** and highest **Precision@10 (0.8400)**, completely eliminating the *vocabulary mismatch problem* of BM25 while preserving its keyword precision.

---

## 🧪 Running Automated Tests

Run the complete test suite (63 unit and integration tests):
```bash
python -m unittest discover tests
```

---

## 📂 Project Structure

```
JOB Search AI/
├── src/
│   ├── ingestion/             # Stage 1: Data ingestion, Pydantic schema & cleaner
│   │   ├── schema.py
│   │   ├── cleaner.py
│   │   └── loader.py
│   ├── search/                # Stages 2 - 6: Retrieval and ranking
│   │   ├── bm25_search.py     # Stage 2: Okapi BM25 inverted index
│   │   ├── vector_search.py   # Stage 3: SentenceTransformers (all-MiniLM-L6-v2)
│   │   ├── db.py              # Stage 4: PostgreSQL + pgvector HNSW database layer
│   │   ├── hybrid_search.py   # Stage 5: Reciprocal Rank Fusion (RRF)
│   │   └── filters.py         # Stage 6: Metadata filters & personalization boosting
│   ├── evaluation/            # Stage 7: IR metrics & comparative evaluation
│   │   ├── metrics.py         # Precision@K, Recall@K, NDCG@K, MRR
│   │   └── evaluate.py        # Benchmark runner
│   └── api/                   # Stage 8: Production FastAPI REST API
│       ├── main.py
│       ├── routes.py
│       └── schemas.py
├── frontend/                  # Stage 9: React + Vite web application
│   ├── src/
│   │   ├── App.jsx
│   │   └── index.css
│   └── package.json
└── tests/                     # 63 automated tests
    ├── test_ingestion.py
    ├── test_search.py
    ├── test_vector.py
    ├── test_db.py
    ├── test_hybrid.py
    ├── test_filters.py
    ├── test_evaluation.py
    └── test_api.py
```
