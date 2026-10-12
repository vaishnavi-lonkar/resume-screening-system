import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..database import get_db
from ..services.parser import ParseError
from ..services.pipeline import candidate_fields, job_fields, ranked_results, rescore_job

router = APIRouter(prefix="/api")


def _job_or_404(db: Session, job_id: int) -> models.Job:
    job = db.get(models.Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    return job


def _job_out(db: Session, job: models.Job) -> schemas.JobOut:
    count = db.scalar(select(func.count()).select_from(models.ScreeningResult)
                      .where(models.ScreeningResult.job_id == job.id)) or 0
    return schemas.JobOut(id=job.id, title=job.title, description=job.description,
                          required_skills=job.required_skills,
                          min_experience_years=job.min_experience_years,
                          min_education_level=job.min_education_level,
                          candidate_count=count, created_at=job.created_at)


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/jobs", response_model=schemas.JobOut, status_code=201)
def create_job(payload: schemas.JobCreate, db: Session = Depends(get_db)):
    job = models.Job(**job_fields(payload.title, payload.description, payload.required_skills))
    db.add(job)
    db.commit()
    return _job_out(db, job)


@router.get("/jobs", response_model=list[schemas.JobOut])
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.scalars(select(models.Job).order_by(models.Job.created_at.desc(), models.Job.id.desc()))
    return [_job_out(db, j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=schemas.JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    return _job_out(db, _job_or_404(db, job_id))


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    db.delete(_job_or_404(db, job_id))
    db.commit()


@router.post("/jobs/{job_id}/screen", response_model=schemas.ScreenResponse)
async def screen(job_id: int, files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    job = _job_or_404(db, job_id)
    errors: list[schemas.FileError] = []
    for upload in files:
        name = upload.filename or "resume"
        data = await upload.read()
        if len(data) > settings.max_upload_bytes:
            errors.append(schemas.FileError(
                filename=name, error=f"File is larger than {settings.max_upload_bytes // 1024 // 1024} MB."))
            continue
        try:
            fields = candidate_fields(name, data)
        except ParseError as exc:
            errors.append(schemas.FileError(filename=name, error=str(exc)))
            continue
        candidate = db.scalar(select(models.Candidate).where(models.Candidate.text_hash == fields["text_hash"]))
        if candidate is None:  # same resume content is stored once
            candidate = models.Candidate(**fields)
            db.add(candidate)
            db.flush()
        exists = db.scalar(select(models.ScreeningResult.id).where(
            models.ScreeningResult.job_id == job.id, models.ScreeningResult.candidate_id == candidate.id))
        if exists is None:
            db.add(models.ScreeningResult(job_id=job.id, candidate_id=candidate.id, score=0,
                                          skill_score=0, text_score=0, experience_score=0, education_score=0))
        db.commit()
    rescore_job(db, job)
    return schemas.ScreenResponse(results=ranked_results(db, job.id), errors=errors)


@router.get("/jobs/{job_id}/results", response_model=list[schemas.ResultOut])
def results(job_id: int, db: Session = Depends(get_db)):
    _job_or_404(db, job_id)
    return ranked_results(db, job_id)


@router.get("/jobs/{job_id}/results.csv")
def results_csv(job_id: int, db: Session = Depends(get_db)):
    job = _job_or_404(db, job_id)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["rank", "name", "email", "phone", "score", "skills_score", "text_score",
                "experience_score", "education_score", "experience_years", "matched_skills",
                "missing_skills", "file"])
    for r in ranked_results(db, job_id):
        w.writerow([r.rank, r.name, r.email or "", r.phone or "", r.score, r.skill_score, r.text_score,
                    r.experience_score, r.education_score, r.experience_years,
                    "; ".join(r.matched_skills), "; ".join(r.missing_skills), r.filename])
    filename = "".join(c if c.isalnum() else "_" for c in job.title)[:50] or "job"
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{filename}_ranking.csv"'})


@router.delete("/candidates/{candidate_id}", status_code=204)
def delete_candidate(candidate_id: int, db: Session = Depends(get_db)):
    cand = db.get(models.Candidate, candidate_id)
    if not cand:
        raise HTTPException(404, "Candidate not found.")
    job_ids = {r.job_id for r in cand.results}
    db.delete(cand)
    db.commit()
    for jid in job_ids:
        rescore_job(db, db.get(models.Job, jid))
