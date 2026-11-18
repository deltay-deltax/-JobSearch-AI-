# JobSearch AI — Project Development & Learning Roadmap

**Project:** Semantic Job Discovery & Recommendation Engine  
**Goal:** Build an end-to-end intelligent job search system demonstrating semantic retrieval, hybrid search, ranking, personalization and search evaluation.

**Target audience:** Software engineering / AI engineering recruiters  
**Primary target:** Elip (YC W25)  
**Development approach:** Incremental MVP — understand → implement → test → improve.

---

# 1. Project Vision

## What are we building?

JobSearch AI is an intelligent job discovery platform that allows users to search for jobs using natural language instead of relying exclusively on traditional keyword-based search.

### Example

A user searches:

"I am a fresher looking for backend engineering internships in Bangalore involving Python, FastAPI or Node.js."

The system should understand the intent, retrieve relevant job listings and rank them according to relevance.

It should return:
- Relevant job listings.
- Match/relevance scores.
- Matching skills.
- Location and experience information.
- Why each job was retrieved.

### Core engineering objective

Build a search and retrieval engine that can:

1. Ingest and process job listings.
2. Convert job descriptions into numerical vector embeddings.
3. Retrieve semantically similar jobs.
4. Combine semantic and keyword-based search.
5. Rank results according to relevance.
6. Evaluate retrieval quality.

The search engine is the main product. The frontend is only the interface through which we demonstrate it.

---

# 2. Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Backend | Python + FastAPI | APIs and business logic |
| Embeddings | Sentence Transformers | Convert text into vectors |
| Vector database | PostgreSQL + pgvector | Store and search embeddings |
| Keyword search | BM25 | Traditional keyword retrieval |
| Hybrid ranking | Reciprocal Rank Fusion | Combine search results |
| Frontend | React + Vite | Search interface |
| Data processing | Python | Clean and process job listings |
| Deployment | Docker | Containerization |

**Important:** We will start with a lightweight implementation and introduce PostgreSQL/pgvector once we understand vector search. We will not introduce every technology on day one.

---

# 3. Project Architecture

The final system will follow this pipeline:

User Query → Query Processing → Retrieval → Ranking → Results

Detailed architecture:

1. **Data ingestion:** Collect job descriptions and relevant metadata.
2. **Data preprocessing:** Clean descriptions, extract relevant fields and remove duplicates.
3. **Embedding generation:** Convert job descriptions into vector representations.
4. **Vector indexing:** Store vectors alongside job metadata.
5. **Query processing:** Accept and process natural-language queries.
6. **Semantic retrieval:** Retrieve jobs using vector similarity.
7. **Keyword retrieval:** Retrieve jobs using BM25.
8. **Hybrid ranking:** Combine retrieval results using RRF.
9. **Metadata filtering:** Apply location, experience and job-type constraints.
10. **API and UI:** Expose search results through FastAPI and React.

---

# 4. Incremental Development Stages

Each stage adds a working capability to the previous stage.

## STAGE 0 — Understand the Search Problem

**Objective:** Understand what we are solving before writing code.

Learn these concepts:

- What is an information retrieval system?
- How does traditional keyword search work?
- What is semantic search?
- Why do keyword-based systems fail?
- What are embeddings?
- What is similarity search?
- What is ranking?

### Practical exercise

Consider these two queries:

Query A: "Python backend developer"

Query B: "I want to build APIs and server-side applications using Python."

A keyword search might struggle to identify their similarity.

A semantic search engine should recognize that both queries express similar intent.

### Completion criteria

- [ ] Understand keyword search.
- [ ] Understand semantic search.
- [ ] Understand embeddings conceptually.
- [ ] Explain why vector search is useful.

**Deliverable:** A written understanding of how our search engine will work.

---

## STAGE 1 — Build the Job Dataset

**Objective:** Create the foundation of our search engine.

We need actual job listings before implementing search.

### Job data structure

Each job should contain:

- id
- title
- company
- description
- skills
- location
- experience_required
- employment_type
- salary (if available)
- application_url

### Implementation

1. Obtain a dataset of job descriptions.
2. Load the dataset using Python.
3. Understand the structure.
4. Clean missing and malformed fields.
5. Remove duplicate listings.
6. Store the processed records.

Start with approximately 500–1,000 listings if available.

### Concepts to learn

- JSON and CSV processing.
- Python dictionaries and lists.
- Data normalization.
- Missing-value handling.
- Basic database design.

### Completion criteria

- [ ] Dataset loaded successfully.
- [ ] Consistent job schema.
- [ ] Duplicate records removed.
- [ ] Clean data available for indexing.

**Deliverable:** A clean job dataset ready for search.

---

## STAGE 2 — Build Traditional Keyword Search

**Objective:** Implement our first working search engine without AI.

Before introducing embeddings, we must understand traditional retrieval.

### Implementation

Build a search function that accepts a query and finds jobs based on matching keywords.

Example:

Input: "Python backend internship"

The system searches job titles, skills and descriptions.

Initially, use simple keyword matching. Then implement BM25.

### Learn

- Tokenization.
- Term frequency.
- Inverse document frequency.
- BM25 scoring.
- Relevance ranking.

### Important questions

1. Why is keyword matching insufficient?
2. What is TF-IDF?
3. How does BM25 improve traditional retrieval?
4. Why can BM25 miss semantically relevant results?

### Completion criteria

- [ ] Search jobs using keywords.
- [ ] Return ranked results.
- [ ] Understand BM25 scoring.
- [ ] Identify limitations of keyword search.

**Deliverable:** A working BM25-based job search engine.

---

## STAGE 3 — Implement Embeddings

**Objective:** Convert job descriptions into numerical representations.

This is where semantic search begins.

### What are embeddings?

Embeddings are numerical vectors that represent the semantic meaning of text.

For example:

"Python backend developer"

and

"Server-side engineer working with Python"

Should produce vectors that are relatively close in embedding space.

### Implementation

1. Install Sentence Transformers.
2. Select a suitable pretrained embedding model.
3. Generate embeddings for every job description.
4. Understand vector dimensions.
5. Store embeddings with their corresponding job IDs.
6. Generate embeddings for incoming queries.

### Concepts to learn

- What is a vector?
- What is an embedding model?
- What is semantic similarity?
- What is cosine similarity?
- Why does vector dimensionality matter?
- What is an embedding space?

### Completion criteria

- [ ] Generate embeddings for job listings.
- [ ] Generate embeddings for user queries.
- [ ] Calculate cosine similarity.
- [ ] Retrieve the most similar job descriptions.

**Deliverable:** A basic semantic search engine.

---

## STAGE 4 — Implement Vector Search

**Objective:** Make semantic retrieval scalable and structured.

Move from basic in-memory similarity calculations to a vector database.

### Implementation

1. Set up PostgreSQL.
2. Install pgvector.
3. Create a jobs table.
4. Store job embeddings.
5. Generate embeddings for search queries.
6. Retrieve nearest vectors.
7. Return matching job records.

### Concepts to learn

- What is a vector database?
- What is pgvector?
- What is nearest-neighbour search?
- What is cosine distance?
- What is an index?
- What is approximate nearest-neighbour search?

### Completion criteria

- [ ] PostgreSQL configured.
- [ ] pgvector enabled.
- [ ] Job embeddings stored.
- [ ] Similarity search working.
- [ ] Results returned with job metadata.

**Deliverable:** A database-backed semantic retrieval engine.

---

## STAGE 5 — Hybrid Search with Reciprocal Rank Fusion

**Objective:** Combine the strengths of keyword and semantic search.

This is one of the most important stages of the project.

### Why hybrid search?

BM25 is excellent at finding exact keyword matches.

Vector search is excellent at finding semantic similarities.

Neither is perfect independently.

We combine both to improve retrieval.

### Architecture

User Query

→ BM25 Retrieval

→ Vector Retrieval

→ Reciprocal Rank Fusion

→ Combined Ranked Results

### Learn Reciprocal Rank Fusion (RRF)

RRF combines ranked lists using:

RRF Score(d) = Σ 1 / (k + rank(d))

Where:

- d = document/job.
- k = a constant, commonly 60.
- rank(d) = position of the document in a retrieval list.

A document ranked highly by multiple retrieval systems receives a stronger combined score.

### Implementation

1. Retrieve the top K jobs using BM25.
2. Retrieve the top K jobs using vector search.
3. Combine the ranked lists.
4. Calculate RRF scores.
5. Sort jobs by their combined scores.
6. Return the final top results.

### Completion criteria

- [ ] BM25 retrieval working.
- [ ] Vector retrieval working.
- [ ] RRF implemented.
- [ ] Duplicate results merged.
- [ ] Combined ranking verified.

**Deliverable:** A hybrid job search engine.

---

## STAGE 6 — Metadata Filtering and Personalization

**Objective:** Make search results more relevant to individual users.

Semantic similarity alone is insufficient.

A user may find a job semantically relevant, but it might be in the wrong location or require five years of experience.

### Filters to implement

- Location.
- Experience level.
- Employment type.
- Job title.
- Skills.
- Salary range, where available.

### Personalization

Allow users to specify preferences:

- Preferred technologies.
- Desired location.
- Experience level.
- Target roles.

Use these preferences to improve retrieval and ranking.

### Completion criteria

- [ ] Location filtering.
- [ ] Experience filtering.
- [ ] Employment type filtering.
- [ ] User preference support.
- [ ] Relevant results prioritized.

**Deliverable:** Personalized job discovery.

---

## STAGE 7 — Search Evaluation

**Objective:** Prove that our search engine actually works.

We should not claim that hybrid search is better without measuring it.

### Create a test dataset

Prepare approximately 20–30 natural-language search queries.

For each query, manually identify relevant job listings.

Use these relevance labels to evaluate retrieval quality.

### Metrics to implement

**1. Precision@K**

Of the top K results returned, how many are relevant?

Precision@K = Relevant results in top K / K

**2. Recall@K**

Of all relevant jobs, how many were retrieved in the top K?

Recall@K = Relevant results in top K / Total relevant results

**3. NDCG@K**

Measures how effectively the search engine places highly relevant results near the top.

### Compare three approaches

- BM25 only.
- Vector search only.
- Hybrid search using RRF.

Record the results in a comparison table.

### Completion criteria

- [ ] Test queries created.
- [ ] Relevance labels assigned.
- [ ] Precision@K calculated.
- [ ] Recall@K calculated.
- [ ] NDCG@K calculated.
- [ ] Retrieval approaches compared.

**Deliverable:** A measurable evaluation of search quality.

---

## STAGE 8 — Build the Backend API

**Objective:** Expose the search engine through production-style APIs.

Use FastAPI.

### Required endpoints

POST /api/search

Accepts a natural-language query and returns ranked results.

GET /api/jobs/{id}

Returns a specific job.

GET /api/health

Checks backend availability.

### Example search request

{
  "query": "Python backend internship for freshers",
  "location": "Bangalore",
  "experience": "Fresher",
  "top_k": 10
}

### Example response

{
  "query": "Python backend internship for freshers",
  "results": [
    {
      "job_id": "101",
      "title": "Backend Developer Intern",
      "company": "Example Company",
      "score": 0.91,
      "matched_skills": ["Python", "FastAPI"]
    }
  ]
}

Scores and matched skills must come from the actual retrieval and ranking pipeline.

### Completion criteria

- [ ] FastAPI application.
- [ ] Search endpoint.
- [ ] Job details endpoint.
- [ ] Input validation.
- [ ] Error handling.
- [ ] API documentation.

**Deliverable:** Working search API.

---

## STAGE 9 — Frontend and Deployment

**Objective:** Turn the backend into a usable product.

### Frontend features

- Natural-language search bar.
- Search filters.
- Job result cards.
- Company and location information.
- Relevance scores.
- Matched skills.
- Job details page.
- External application links.

Keep the design clean and simple.

### Deployment

- Backend: Dockerized FastAPI.
- Database: PostgreSQL with pgvector.
- Frontend: React deployment.
- Environment variables for configuration.
- README with setup instructions.

### Completion criteria

- [ ] Search interface.
- [ ] Backend connected.
- [ ] Results displayed.
- [ ] Filters working.
- [ ] Application links working.
- [ ] Deployed application.
- [ ] GitHub README.

**Deliverable:** Publicly accessible JobSearch AI MVP.

---

# 5. Final Feature Scope

The following is the intended final project scope.

| Feature | Importance |
|---|---|
| Job ingestion | Essential |
| Keyword search | Essential |
| Embeddings | Essential |
| Semantic retrieval | Essential |
| Vector database | Essential |
| BM25 | Essential |
| Hybrid search | Essential |
| RRF ranking | Essential |
| Metadata filtering | Essential |
| Search evaluation | Essential |
| FastAPI backend | Essential |
| React interface | Essential |
| Personalization | Enhancement |
| LLM-generated explanations | Enhancement |
| AI career chatbot | Out of scope |
| Agent memory | Out of scope |
| Authentication | Out of scope |

---

# 6. One-Day MVP Execution Plan

Since the application deadline is close, we will prioritize a working technical demonstration over completing every planned stage.

| Time allocation | Work |
|---|---|
| Hour 1 | Dataset and preprocessing |
| Hours 2–3 | BM25 and semantic search |
| Hours 4–5 | Hybrid retrieval and RRF |
| Hour 6 | FastAPI integration |
| Hour 7 | Basic React interface |
| Hour 8 | Testing, README and deployment attempt |

**Priority:** Working retrieval engine → evaluation → API → UI.

If deployment takes longer, provide a reproducible local setup rather than sacrificing the search engine.

---

# 7. How We Will Learn and Build Together

This is the most important part of the development process.

We will not jump directly into implementation.

For every stage, follow this cycle:

### Step 1 — Understand

Learn the underlying concept.

Example: Before implementing embeddings, understand what vectors are and why they represent semantic meaning.

### Step 2 — Small example

Work through a simple example manually.

Example: Calculate cosine similarity between two vectors.

### Step 3 — Implementation

Write the actual code, understanding each important line.

### Step 4 — Dry run

Trace the data through the implementation.

Understand:
- Input.
- Intermediate processing.
- Output.
- Edge cases.

### Step 5 — Testing

Test normal cases, edge cases and failure scenarios.

### Step 6 — Interview preparation

Answer questions about:
- Why we chose this approach.
- How it works internally.
- Its time and space complexity.
- Its limitations.
- Alternative approaches.

Only then move to the next stage.

---

# 8. Interview Readiness Checklist

By the end, I should be able to confidently explain:

**Search fundamentals**
- Keyword search vs semantic search.
- BM25 and TF-IDF.
- Embeddings and vector similarity.
- Cosine similarity.

**Retrieval engineering**
- Vector databases.
- Nearest-neighbour search.
- Hybrid search.
- Reciprocal Rank Fusion.
- Reranking.

**Recommendation systems**
- Relevance scoring.
- Personalization.
- Metadata filtering.
- Recommendation quality.

**Evaluation**
- Precision@K.
- Recall@K.
- NDCG@K.

**Backend engineering**
- FastAPI.
- PostgreSQL.
- API design.
- Data ingestion.
- Error handling.
- Docker.

---

# 9. Definition of Done

The project is considered complete when:

- A user can enter a natural-language query.
- The engine can search a real job dataset.
- Semantic and keyword retrieval both work.
- Hybrid ranking produces a combined result list.
- Users can filter results by metadata.
- Search quality can be evaluated quantitatively.
- Results are accessible through an API.
- A working frontend demonstrates the system.
- The complete project is documented on GitHub.

**Final principle:**

We are not building an AI wrapper around a search bar.

We are building an actual information retrieval system, understanding the fundamentals behind it and demonstrating how it can power an intelligent recommendation product.

**Let's build it one stage at a time.**