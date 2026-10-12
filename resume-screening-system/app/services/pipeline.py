"""Glue between parsing, extraction, scoring and the database."""
import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from .extractor import extract_required_education, extract_required_years, parse_resume
from .parser import extract_text
from .scoring import CandidateProfile, JobProfile, score_candidates
from .skills import canonical, extract_skills
from .textutil import clean_for_matching, normalize


def job_fields(title: str, description: str, required: list[str] | None) -> dict:
    description = normalize(description)
    if required:
        skills = sorted({canonical(s) for s in required if s.strip()})
    else:
        skills = extract_skills(description)
    return {
        "title": title.strip(),
        "description": description,
        "required_skills": skills,
        "min_experience_years": extract_required_years(description),
        "min_education_level": extract_required_education(description),
    }


def candidate_fields(filename: str, data: bytes) -> dict:
    """Raises ParseError for unreadable files."""
    text = normalize(extract_text(filename, data))
    fields = parse_resume(text, filename)
    fields.update(
        filename=filename,
        raw_text=text,
        text_hash=hashlib.sha256(clean_for_matching(text).encode()).hexdigest(),
    )
    return fields


def rescore_job(db: Session, job: models.Job) -> None:
    """Score every candidate screened for this job against the job description in one batch,
    so TF-IDF weights (and therefore scores) stay consistent across uploads."""
    results = list(db.scalars(select(models.ScreeningResult).where(models.ScreeningResult.job_id == job.id)))
    if not results:
        return
    jp = JobProfile(clean_for_matching(job.description), job.required_skills,
                    job.min_experience_years, job.min_education_level)
    cps = [CandidateProfile(clean_for_matching(r.candidate.raw_text), r.candidate.skills,
                            r.candidate.experience_years, r.candidate.education_level) for r in results]
    for r, s in zip(results, score_candidates(jp, cps)):
        r.score, r.skill_score, r.text_score = s.total, s.skill, s.text
        r.experience_score, r.education_score = s.experience, s.education
        r.matched_skills, r.missing_skills = s.matched, s.missing
    db.commit()


def ranked_results(db: Session, job_id: int) -> list[schemas.ResultOut]:
    rows = db.scalars(
        select(models.ScreeningResult).where(models.ScreeningResult.job_id == job_id)
        .order_by(models.ScreeningResult.score.desc(), models.ScreeningResult.id)
    ).all()
    return [result_out(r, i) for i, r in enumerate(rows, 1)]


def result_out(r: models.ScreeningResult, rank: int) -> schemas.ResultOut:
    from .extractor import EDU_LABELS

    c = r.candidate
    return schemas.ResultOut(
        result_id=r.id, rank=rank, candidate_id=c.id, name=c.name, email=c.email, phone=c.phone,
        links=c.links, filename=c.filename, score=r.score, skill_score=r.skill_score,
        text_score=r.text_score, experience_score=r.experience_score,
        education_score=r.education_score, matched_skills=r.matched_skills,
        missing_skills=r.missing_skills, skills=c.skills, experience_years=c.experience_years,
        education=c.education, education_label=EDU_LABELS[c.education_level],
        certifications=c.certifications, projects=c.projects,
    )
