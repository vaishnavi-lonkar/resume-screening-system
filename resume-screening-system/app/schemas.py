from datetime import datetime

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=20)
    required_skills: list[str] | None = None  # optional override; otherwise extracted


class JobOut(BaseModel):
    id: int
    title: str
    description: str
    required_skills: list[str]
    min_experience_years: float | None
    min_education_level: int
    candidate_count: int = 0
    created_at: datetime


class ResultOut(BaseModel):
    result_id: int
    rank: int
    candidate_id: int
    name: str
    email: str | None
    phone: str | None
    links: list[str]
    filename: str
    score: float
    skill_score: float
    text_score: float
    experience_score: float
    education_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    skills: list[str]
    experience_years: float
    education: list[str]
    education_label: str
    certifications: list[str]
    projects: list[str]


class FileError(BaseModel):
    filename: str
    error: str


class ScreenResponse(BaseModel):
    results: list[ResultOut]
    errors: list[FileError]
