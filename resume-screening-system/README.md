# Shortlist: Resume Screening System

Upload a job description and a batch of resumes (PDF, DOCX or TXT). The system extracts each candidate's
skills, education, experience, certifications and projects, scores them against the job, and returns a ranked list.

## Features

- Resume parsing: PDF (`pypdf`), DOCX (`python-docx`, including tables) and TXT
- Information extraction: name, email, phone, GitHub/LinkedIn links, skills (taxonomy of ~150 skills with aliases),
  education level, years of experience (from date ranges and "N years" statements), certifications, projects
- Relevance score (0-100) built from four parts, each shown in the UI:

  | Part | Default weight | How it is computed |
  |---|---|---|
  | Skills | 45% | Share of the job's required skills found in the resume |
  | Text match | 30% | TF-IDF (1-2 grams) cosine similarity between job and resume; optional transformer embeddings |
  | Experience | 15% | Candidate years / years the job asks for |
  | Education | 10% | Candidate degree level / level the job asks for |

- Ranked results with matched and missing skills, contact details, CSV export
- Duplicate resumes (same content) are stored once; scores are recalculated for the whole job after every upload
- FastAPI backend, SQLAlchemy models (SQLite, PostgreSQL or MySQL), no-build HTML/CSS/JS frontend

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000. Interactive API docs are at http://localhost:8000/docs.

Try it with the files in `sample_data/`: create a job from `job_description.txt`, then upload the `resume_*.txt` files.
`python scripts/make_sample_docx.py` creates DOCX versions.

### Docker (PostgreSQL)

```bash
docker compose up --build
```

## Configuration

Copy `.env.example` to `.env` or set environment variables.

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./resume_screening.db` | For PostgreSQL install `psycopg2-binary`, for MySQL install `pymysql` |
| `MAX_UPLOAD_MB` | `5` | Per resume |
| `USE_TRANSFORMERS` | `false` | `true` blends sentence-transformer similarity into the text score (`pip install sentence-transformers`) |
| `WEIGHT_*` | see table | Re-normalised to sum to 1. The colour bar in the UI assumes the default weights |

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/jobs` | Create a job `{title, description, required_skills?}` |
| GET | `/api/jobs`, `/api/jobs/{id}` | List / fetch jobs |
| DELETE | `/api/jobs/{id}` | Delete a job and its rankings |
| POST | `/api/jobs/{id}/screen` | Upload resumes (`multipart`, field `files`); returns `{results, errors}` |
| GET | `/api/jobs/{id}/results` | Ranked candidates |
| GET | `/api/jobs/{id}/results.csv` | CSV export |
| DELETE | `/api/candidates/{id}` | Remove a candidate |

## Project layout

```
app/
  main.py            FastAPI app, serves the frontend
  config.py          settings from environment
  database.py        SQLAlchemy engine and session
  models.py          Job, Candidate, ScreeningResult
  schemas.py         request/response models
  routers/jobs.py    REST endpoints
  services/
    parser.py        PDF / DOCX / TXT to text
    textutil.py      cleaning and normalisation
    skills.py        skill taxonomy and matching (edit TAXONOMY to add skills)
    extractor.py     sections, contact, education, experience, certifications, projects
    scoring.py       TF-IDF / transformer similarity and weighted score
    pipeline.py      glue between parsing, scoring and the database
frontend/            index.html, style.css, app.js
tests/               pytest suite
sample_data/         example job description and resumes
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Known limitations

- Scanned or image-only PDFs have no text layer and are rejected with a clear message; add OCR (for example `pytesseract`) in `services/parser.py` if you need them.
- Extraction is rule-based. Unusual layouts (multi-column PDFs, graphics-heavy templates) can reduce accuracy. Year-only date ranges (`2021 - 2024`) can overstate experience by up to a year.
- Skills are matched against the built-in taxonomy; unknown skills can still be required by listing them in the job's "Required skills" field and are matched as plain words.
- The job description's wording decides what counts as required: "plus" or "nice to have" skills are treated like required ones unless you override the skill list.
- There is no login. Add authentication before exposing this beyond a trusted network, since resumes contain personal data.
- Scores support, not replace, a recruiter's judgement. Review how the weights behave on your own roles before relying on rankings.
