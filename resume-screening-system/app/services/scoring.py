"""Relevance scoring: skill match + TF-IDF / semantic similarity + experience + education."""
from dataclasses import dataclass, field

from ..config import settings
from .skills import contains_term


@dataclass
class JobProfile:
    description: str  # cleaned text
    required_skills: list[str]
    min_years: float | None
    min_education_level: int


@dataclass
class CandidateProfile:
    text: str  # cleaned text
    skills: list[str]
    years: float
    education_level: int


@dataclass
class Score:
    total: float
    skill: float
    text: float
    experience: float
    education: float
    matched: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


_embedder = None


def _semantic_similarities(job_text: str, texts: list[str]) -> list[float] | None:
    """Optional transformer similarity; returns None when disabled or unavailable."""
    global _embedder
    if not settings.use_transformers:
        return None
    try:
        from sentence_transformers import SentenceTransformer, util

        if _embedder is None:
            _embedder = SentenceTransformer(settings.transformer_model)
        vecs = _embedder.encode([job_text] + texts, convert_to_tensor=True, normalize_embeddings=True)
        return [max(0.0, float(s)) for s in util.cos_sim(vecs[0], vecs[1:])[0]]
    except Exception:  # noqa: BLE001 - fall back to TF-IDF only
        return None


def _tfidf_similarities(job_text: str, texts: list[str]) -> list[float]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True, min_df=1)
    try:
        matrix = vec.fit_transform([job_text] + texts)
    except ValueError:  # empty vocabulary
        return [0.0] * len(texts)
    return [float(s) for s in cosine_similarity(matrix[0], matrix[1:])[0]]


def _education_score(candidate: int, required: int) -> float:
    if required == 0:
        return min(1.0, candidate / 2) if candidate else 0.5
    return min(1.0, candidate / required)


def _experience_score(years: float, required: float | None) -> float:
    if not required:
        return min(1.0, years / 3) if years else 0.5
    return min(1.0, years / required)


def score_candidates(job: JobProfile, candidates: list[CandidateProfile]) -> list[Score]:
    if not candidates:
        return []
    texts = [c.text for c in candidates]
    tfidf = _tfidf_similarities(job.description, texts)
    semantic = _semantic_similarities(job.description, texts)

    w = {"skill": settings.w_skills, "text": settings.w_text,
         "exp": settings.w_experience, "edu": settings.w_education}
    if not job.required_skills:  # nothing to match on: lean on text similarity
        w["text"] += w.pop("skill")
    norm = sum(w.values()) or 1.0

    results = []
    for cand, tf, i in zip(candidates, tfidf, range(len(candidates))):
        text_sim = tf / settings.text_similarity_ceiling
        if semantic is not None:
            text_sim = 0.5 * text_sim + 0.5 * semantic[i]
        text_score = min(1.0, text_sim)

        matched = [s for s in job.required_skills if s in cand.skills or contains_term(cand.text, s)]
        missing = [s for s in job.required_skills if s not in matched]
        skill_score = len(matched) / len(job.required_skills) if job.required_skills else 0.0
        exp_score = _experience_score(cand.years, job.min_years)
        edu_score = _education_score(cand.education_level, job.min_education_level)

        total = (w.get("skill", 0) * skill_score + w["text"] * text_score
                 + w["exp"] * exp_score + w["edu"] * edu_score) / norm
        results.append(Score(*(round(x * 100, 1) for x in
                               (total, skill_score, text_score, exp_score, edu_score)),
                             matched=matched, missing=missing))
    return results
