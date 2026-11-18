"""Centralized configuration for JobSearch AI.

This module provides path management, model configuration, and search constants.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Project Root Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data Directories
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EVALUATION_DATA_DIR = DATA_DIR / "evaluation"

# Default Data File Paths
DEFAULT_RAW_JOBS_PATH = RAW_DATA_DIR / "jobs_raw.json"
DEFAULT_PROCESSED_JOBS_PATH = PROCESSED_DATA_DIR / "jobs_cleaned.json"

# Search & Retrieval Hyperparameters
DEFAULT_TOP_K = 10
RRF_K_CONSTANT = 60  # Standard constant in Reciprocal Rank Fusion

# Embedding Model
DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

# PostgreSQL Connection Settings (loaded from .env)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "jobsearch_ai")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Embedding dimensionality for all-MiniLM-L6-v2
EMBEDDING_DIM = 384
