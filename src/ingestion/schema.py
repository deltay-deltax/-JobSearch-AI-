"""Data schema for JobSearch AI.

Defines Pydantic models for raw job inputs and cleaned, validated Job postings.
Ensures consistency across data ingestion, vector search, and API responses.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re


class JobPosting(BaseModel):
    """Cleaned and validated Job Posting entity used across the search engine.
    
    Attributes:
        id: Unique identifier for the job posting.
        title: Standardized job title (e.g. 'Backend Software Engineer').
        company: Company or organization name offering the position.
        description: Full text description of responsibilities and requirements.
        skills: List of extracted/normalized technical and soft skills.
        location: Primary location (e.g. 'Bangalore', 'Remote', 'San Francisco').
        experience_required: Normalized experience level (e.g. 'Fresher', '1-3 years', '3-5 years', '5+ years').
        employment_type: Type of contract ('Full-time', 'Internship', 'Contract', 'Part-time').
        salary: Salary range or compensation details if disclosed.
        application_url: Direct URL to apply for the position.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    id: str = Field(description="Unique identifier for the job listing")
    title: str = Field(min_length=2, description="Job title")
    company: str = Field(min_length=1, description="Hiring company name")
    description: str = Field(min_length=10, description="Detailed job description")
    skills: List[str] = Field(default_factory=list, description="Extracted skills")
    location: str = Field(default="Remote", description="Job location")
    experience_required: str = Field(default="Not Specified", description="Required years of experience")
    employment_type: str = Field(default="Full-time", description="Full-time, Internship, Contract, etc.")
    salary: Optional[str] = Field(default=None, description="Salary or compensation if available")
    application_url: Optional[str] = Field(default=None, description="Application link")

    @field_validator("skills", mode="before")
    @classmethod
    def sanitize_skills(cls, v) -> List[str]:
        """Ensures skills are a clean list of trimmed strings."""
        if v is None:
            return []
        if isinstance(v, str):
            # Split comma or pipe separated skill strings
            items = re.split(r"[,|]", v)
            return [item.strip() for item in items if item.strip()]
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        return []

    def to_searchable_text(self) -> str:
        """Constructs a rich text representation of the job listing.
        
        This composite text is used to compute BM25 tokens and dense vector embeddings.
        Combining title, company, skills, and description ensures that both high-level
        attributes and granular requirements are represented in vector space.
        """
        skills_str = ", ".join(self.skills)
        return (
            f"Title: {self.title}\n"
            f"Company: {self.company}\n"
            f"Location: {self.location} | Type: {self.employment_type} | Experience: {self.experience_required}\n"
            f"Skills: {skills_str}\n"
            f"Description: {self.description}"
        )
