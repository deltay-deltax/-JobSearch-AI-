"""Centralized configuration for JobSearch AI.

This module provides path management, model configuration, and search constants.
"""

from pathlib import Path
import os

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
