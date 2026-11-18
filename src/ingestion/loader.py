"""Dataset loader, exporter, and seed generator for JobSearch AI.

Handles loading raw JSON/CSV job files, persisting processed clean datasets,
and synthesizing a realistic benchmark dataset of software engineering roles.
"""

from typing import List, Dict, Any, Union, Tuple
from pathlib import Path
import json
import csv
import random

from src.ingestion.schema import JobPosting
from src.ingestion.cleaner import JobDataCleaner
from src.config import (
    DEFAULT_RAW_JOBS_PATH,
    DEFAULT_PROCESSED_JOBS_PATH,
)


def load_raw_jobs(file_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """Loads raw job records from either a JSON or CSV file.
    
    Args:
        file_path: Path to the JSON or CSV file.
        
    Returns:
        List of raw job dictionaries.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Job file not found at: {path}")

    if path.suffix.lower() == ".json":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "jobs" in data:
                return data["jobs"]
            else:
                raise ValueError("JSON file must contain a list of records or a top-level 'jobs' key.")

    elif path.suffix.lower() == ".csv":
        records = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # If skills is stored as a stringified list or comma-separated string, keep as string for cleaner
                records.append(dict(row))
        return records

    else:
        raise ValueError(f"Unsupported file format '{path.suffix}'. Please provide .json or .csv.")


def save_processed_jobs(jobs: List[JobPosting], file_path: Union[str, Path]) -> None:
    """Saves cleaned JobPosting objects as formatted JSON.
    
    Args:
        jobs: List of validated JobPosting objects.
        file_path: Output path for the cleaned JSON file.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    serialized = [job.model_dump() for job in jobs]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(serialized, f, indent=2, ensure_ascii=False)


def generate_synthetic_job_pool() -> List[Dict[str, Any]]:
    """Creates a diverse, realistic dataset of software and AI engineering jobs.
    
    Includes positions tailored for freshers, junior, mid, and senior levels across
    Bangalore, Hyderabad, Pune, Gurgaon, and Remote.
    Also injects intentional HTML formatting and duplicate listings to test cleaning.
    """
    companies = [
        ("Elip", "YC W25 AI agents startup building autonomous workflow automation"),
        ("Razorpay", "Fintech unicorn simplifying payments and banking for businesses"),
        ("Postman", "API collaboration platform used by over 30 million developers"),
        ("Swiggy", "Hyperlocal food delivery and quick commerce engineering team"),
        ("Flipkart", "E-commerce platform scaling distributed systems for peak traffic"),
        ("Zerodha", "Bootstrapped fintech powering India's largest discount broker"),
        ("CRED", "Member-only platform rewarding financial discipline with high-scale tech"),
        ("Hasura", "Open-source GraphQL and instant API engine for modern databases"),
        ("BrowserStack", "Cloud-based web and mobile testing infrastructure"),
        ("Ola Krutrim", "Building sovereign foundational AI models and high-throughput inference APIs"),
    ]

    roles = [
        {
            "title": "Backend Engineering Intern",
            "experience": "Fresher / 0 years",
            "type": "Internship",
            "salary": "₹40,000 - ₹60,000 / month",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Git"],
            "desc_template": "<p>We are seeking a high-energy <b>Backend Engineering Intern</b> to help design REST APIs and microservices. You will work directly with our senior engineers using Python and FastAPI. Ideal for fresh graduates passionate about scalable server-side systems.</p>",
        },
        {
            "title": "Junior Python Developer",
            "experience": "1-2 years",
            "type": "Full-time",
            "salary": "₹8,00,000 - ₹12,00,000 PA",
            "skills": ["Python", "Django", "PostgreSQL", "Redis", "Celery"],
            "desc_template": "Looking for a Junior Python Developer with 1+ years of hands-on experience building backend APIs. You will implement data pipelines, asynchronous queues with Celery, and optimize relational database queries.",
        },
        {
            "title": "AI / ML Engineer",
            "experience": "1-3 years",
            "type": "Full-time",
            "salary": "₹15,00,000 - ₹22,00,000 PA",
            "skills": ["Python", "PyTorch", "Hugging Face", "Vector Databases", "LangChain"],
            "desc_template": "<p>Join our core AI team to build semantic retrieval pipelines and fine-tune transformer models. You will implement embedding search using pgvector, optimize vector similarity search, and evaluate retrieval-augmented generation systems.</p>",
        },
        {
            "title": "Senior Backend Architect",
            "experience": "5+ years",
            "type": "Full-time",
            "salary": "₹35,00,000 - ₹50,00,000 PA",
            "skills": ["Go", "Python", "Kubernetes", "Kafka", "PostgreSQL", "Distributed Systems"],
            "desc_template": "We are hiring a Senior Backend Architect to lead our platform reliability and microservices architecture. Requires deep expertise in high-throughput distributed systems, event streams with Kafka, and container orchestration.",
        },
        {
            "title": "Full Stack Engineer (React + Node/Python)",
            "experience": "2-4 years",
            "type": "Full-time",
            "salary": "₹14,00,000 - ₹20,00,000 PA",
            "skills": ["React.js", "Node.js", "FastAPI", "TypeScript", "TailwindCSS"],
            "desc_template": "Seeking an end-to-end builder to craft responsive user interfaces in React while connecting them to robust Python FastAPI backends. Strong product sense and clean API design skills required.",
        },
        {
            "title": "Data Engineer",
            "experience": "2-4 years",
            "type": "Full-time",
            "salary": "₹16,00,000 - ₹24,00,000 PA",
            "skills": ["Python", "Apache Spark", "Airflow", "Snowflake", "SQL"],
            "desc_template": "Design and maintain high-volume ETL pipelines. Responsible for data ingestion from multiple third-party APIs, data transformation using PySpark, and orchestrating batch jobs with Airflow.",
        },
        {
            "title": "DevOps / Platform Engineer",
            "experience": "3-5 years",
            "type": "Full-time",
            "salary": "₹18,00,000 - ₹26,00,000 PA",
            "skills": ["Kubernetes", "Docker", "AWS", "Terraform", "CI/CD"],
            "desc_template": "Automate cloud infrastructure and continuous deployment workflows. Maintain our Kubernetes clusters on AWS, write reusable Terraform modules, and maintain 99.99% uptime.",
        },
        {
            "title": "AI Engineering Intern",
            "experience": "Fresher",
            "type": "Internship",
            "salary": "₹45,000 - ₹65,000 / month",
            "skills": ["Python", "PyTorch", "NLP", "FastAPI", "Scikit-Learn"],
            "desc_template": "Exciting internship opportunity for university students and recent graduates! Learn to build semantic search engines, fine-tune sentence transformers, and deploy AI services to production.",
        },
    ]

    locations = ["Bangalore", "Bangalore (HSR Layout)", "Hyderabad", "Pune", "Gurgaon", "Remote", "Bangalore / Remote"]

    raw_jobs = []
    job_counter = 1

    # Deterministic generation
    random.seed(42)

    for comp_name, comp_about in companies:
        for role in roles:
            loc = random.choice(locations)
            job_id = f"job_{job_counter:04d}"
            
            full_description = (
                f"{role['desc_template']}\n\n"
                f"About {comp_name}: {comp_about}.\n"
                f"Requirements: Demonstrated experience in {', '.join(role['skills'][:3])}. "
                f"Comfortable collaborating in an agile startup environment."
            )

            raw_jobs.append({
                "id": job_id,
                "title": role["title"],
                "company": comp_name,
                "description": full_description,
                "skills": role["skills"],
                "location": loc,
                "experience_required": role["experience"],
                "employment_type": role["type"],
                "salary": role["salary"],
                "application_url": f"https://careers.{comp_name.lower().replace(' ', '')}.com/jobs/{job_id}",
            })
            job_counter += 1

    # Inject deliberate duplicate records with slightly altered IDs to test de-duplication
    if len(raw_jobs) >= 2:
        dup1 = raw_jobs[0].copy()
        dup1["id"] = "job_dup_9999"  # different ID, but identical content
        raw_jobs.append(dup1)

        dup2 = raw_jobs[3].copy()
        dup2["id"] = "job_dup_8888"
        raw_jobs.append(dup2)

    return raw_jobs


def run_stage1_pipeline() -> Tuple[Path, Path, str]:
    """Executes the full Stage 1 pipeline:
    
    1. Generates and stores raw job dataset (data/raw/jobs_raw.json).
    2. Runs JobDataCleaner (HTML stripping, normalization, deduplication).
    3. Saves validated JobPosting records (data/processed/jobs_cleaned.json).
    4. Returns summary.
    """
    # 1. Generate & save raw data
    raw_data = generate_synthetic_job_pool()
    DEFAULT_RAW_JOBS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DEFAULT_RAW_JOBS_PATH, "w", encoding="utf-8") as f:
        json.dump(raw_data, f, indent=2, ensure_ascii=False)

    # 2. Clean and process
    cleaner = JobDataCleaner()
    clean_jobs = cleaner.process_batch(raw_data)

    # 3. Save processed records
    save_processed_jobs(clean_jobs, DEFAULT_PROCESSED_JOBS_PATH)

    summary = cleaner.get_summary_report()
    return DEFAULT_RAW_JOBS_PATH, DEFAULT_PROCESSED_JOBS_PATH, summary


if __name__ == "__main__":
    raw_p, proc_p, report = run_stage1_pipeline()
    print(f"Raw jobs written to: {raw_p}")
    print(f"Cleaned jobs written to: {proc_p}")
    print(report)
