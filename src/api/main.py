"""FastAPI Application Entry Point for JobSearch AI.

Runs with:
    uvicorn src.api.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.ingestion.loader import load_raw_jobs
from src.ingestion.schema import JobPosting
from src.search.filters import PersonalizedSearchEngine
from src.api.routes import router, set_engine
from src.config import DEFAULT_PROCESSED_JOBS_PATH


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes models and search indexes on startup."""
    print("Initializing JobSearch AI search engine...")
    raw = load_raw_jobs(DEFAULT_PROCESSED_JOBS_PATH)
    jobs = [JobPosting(**item) for item in raw]

    engine = PersonalizedSearchEngine()
    engine.fit(jobs)
    set_engine(engine)
    print(f"✓ Search engine ready with {len(jobs)} jobs indexed.")
    yield
    print("Shutting down JobSearch AI.")


app = FastAPI(
    title="JobSearch AI API",
    description="Intelligent Semantic Job Discovery & Recommendation Engine",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for React frontend (Vite default port 5173 and 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
