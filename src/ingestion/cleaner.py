"""Data cleaner and normalizer for JobSearch AI.

Handles text sanitization, HTML stripping, skill canonicalization,
experience-level normalization, and content-hash deduplication.
"""

from typing import List, Dict, Any, Tuple, Optional
import re
import hashlib
from bs4 import BeautifulSoup

from src.ingestion.schema import JobPosting


# Canonical mapping for common tech skill variants
SKILL_SYNONYMS = {
    "py": "python",
    "python3": "python",
    "fast-api": "fastapi",
    "fast api": "fastapi",
    "react.js": "react",
    "reactjs": "react",
    "node": "node.js",
    "nodejs": "node.js",
    "postgres": "postgresql",
    "psql": "postgresql",
    "mongo": "mongodb",
    "k8s": "kubernetes",
    "aws": "amazon web services",
    "gcp": "google cloud",
    "docker": "docker",
    "machine learning": "ml",
    "artificial intelligence": "ai",
}


def strip_html(text: str) -> str:
    """Removes HTML markup and unescapes HTML entities.
    
    Many scraped job listings contain embedded HTML (<p>, <li>, &amp;).
    This converts raw HTML to clean plaintext.
    """
    if not text:
        return ""
    # Use BeautifulSoup with standard html.parser
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ")


def clean_text(text: str) -> str:
    """Normalizes text by removing HTML, unicode anomalies, and extra whitespace."""
    if not text:
        return ""
    # Strip HTML tags
    cleaned = strip_html(text)
    # Replace non-breaking spaces and unusual whitespace
    cleaned = cleaned.replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple consecutive whitespaces into a single space
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    # Collapse 3+ newlines into 2
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def normalize_skill(skill: str) -> str:
    """Canonicalizes a single skill token (e.g. 'React.js' -> 'react')."""
    cleaned = skill.strip().lower()
    return SKILL_SYNONYMS.get(cleaned, cleaned)


def normalize_skills(skills: List[str]) -> List[str]:
    """Cleans, normalizes, and deduplicates a list of skills preserving order."""
    normalized = []
    seen = set()
    for s in skills:
        canon = normalize_skill(s)
        if canon and canon not in seen:
            seen.add(canon)
            normalized.append(canon)
    return normalized


def normalize_experience(exp_str: str) -> str:
    """Standardizes experience text into unified buckets:
    
    - 'Fresher' (0 years, interns, entry-level, new grads)
    - '1-3 years' (Junior to Mid)
    - '3-5 years' (Mid-level)
    - '5+ years' (Senior / Staff / Lead)
    """
    if not exp_str:
        return "Not Specified"

    lower = exp_str.lower().strip()

    if any(k in lower for k in ["fresher", "intern", "0 year", "entry level", "new grad", "0-1 year"]):
        return "Fresher"

    # Search for numeric patterns like "3-5 years" or "2+ years"
    match = re.search(r"(\d+)\s*[-to]+\s*(\d+)", lower)
    if match:
        min_years = int(match.group(1))
        if min_years >= 5:
            return "5+ years"
        elif min_years >= 3:
            return "3-5 years"
        elif min_years >= 1:
            return "1-3 years"
        else:
            return "Fresher"

    single_num = re.search(r"(\d+)\s*\+?\s*year", lower)
    if single_num:
        years = int(single_num.group(1))
        if years >= 5:
            return "5+ years"
        elif years >= 3:
            return "3-5 years"
        elif years >= 1:
            return "1-3 years"
        else:
            return "Fresher"

    if any(k in lower for k in ["senior", "lead", "principal", "staff"]):
        return "5+ years"

    return exp_str.strip()


def compute_content_fingerprint(title: str, company: str, description: str) -> str:
    """Computes an MD5 hash of normalized title, company, and description.
    
    This fingerprint detects exact and near-exact duplicate postings across
    different scraped sources or repetitive job board uploads.
    """
    norm_title = re.sub(r"\W+", "", title.lower())
    norm_company = re.sub(r"\W+", "", company.lower())
    # Take first 300 alphanumeric chars of description to catch duplicates even if footer differs
    norm_desc = re.sub(r"\W+", "", description.lower())[:300]
    
    payload = f"{norm_company}:{norm_title}:{norm_desc}".encode("utf-8")
    return hashlib.md5(payload).hexdigest()


class JobDataCleaner:
    """Pipeline processor to clean, normalize, validate, and deduplicate job records."""

    def __init__(self):
        self.seen_fingerprints = set()
        self.stats = {
            "total_input": 0,
            "valid_records": 0,
            "dropped_duplicates": 0,
            "dropped_invalid": 0,
        }

    def process_record(self, raw: Dict[str, Any]) -> Optional[JobPosting]:
        """Cleans and validates a single job record dictionary."""
        self.stats["total_input"] += 1

        try:
            # 1. Clean textual fields
            title = clean_text(str(raw.get("title", "")))
            company = clean_text(str(raw.get("company", "")))
            description = clean_text(str(raw.get("description", "")))
            location = clean_text(str(raw.get("location", "Remote"))) or "Remote"
            raw_exp = str(raw.get("experience_required", ""))
            experience_required = normalize_experience(raw_exp)
            employment_type = clean_text(str(raw.get("employment_type", "Full-time"))) or "Full-time"
            salary = raw.get("salary")
            if salary:
                salary = clean_text(str(salary))
            application_url = raw.get("application_url")
            if application_url:
                application_url = str(application_url).strip()

            # 2. Normalize and sanitize skills
            raw_skills = raw.get("skills", [])
            if isinstance(raw_skills, str):
                raw_skills = re.split(r"[,|]", raw_skills)
            normalized_skills = normalize_skills(raw_skills)

            # 3. Check for duplicates using content fingerprint
            fingerprint = compute_content_fingerprint(title, company, description)
            if fingerprint in self.seen_fingerprints:
                self.stats["dropped_duplicates"] += 1
                return None

            # 4. Construct Pydantic model
            job = JobPosting(
                id=str(raw.get("id", f"job_{self.stats['valid_records'] + 1}")),
                title=title,
                company=company,
                description=description,
                skills=normalized_skills,
                location=location,
                experience_required=experience_required,
                employment_type=employment_type,
                salary=salary,
                application_url=application_url,
            )

            # Register fingerprint
            self.seen_fingerprints.add(fingerprint)
            self.stats["valid_records"] += 1
            return job

        except Exception:
            # Catch Pydantic validation errors or missing mandatory fields
            self.stats["dropped_invalid"] += 1
            return None

    def process_batch(self, raw_records: List[Dict[str, Any]]) -> List[JobPosting]:
        """Processes a full batch of raw records, returning clean JobPosting objects."""
        clean_jobs = []
        for record in raw_records:
            job = self.process_record(record)
            if job:
                clean_jobs.append(job)
        return clean_jobs

    def get_summary_report(self) -> str:
        """Returns a formatted human-readable summary of the cleaning execution."""
        return (
            f"=== Ingestion Summary ===\n"
            f"Total Processed:    {self.stats['total_input']}\n"
            f"Successfully Clean: {self.stats['valid_records']}\n"
            f"Dropped Duplicates: {self.stats['dropped_duplicates']}\n"
            f"Dropped Invalid:    {self.stats['dropped_invalid']}\n"
            f"========================="
        )
