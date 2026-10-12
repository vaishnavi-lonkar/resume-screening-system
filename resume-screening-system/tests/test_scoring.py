from app.services.scoring import CandidateProfile, JobProfile, score_candidates


def test_better_match_ranks_higher():
    job = JobProfile("python sql machine learning pandas dashboards", ["python", "sql", "pandas"], 1, 2)
    strong = CandidateProfile("python sql pandas machine learning dashboards", ["python", "sql", "pandas"], 2, 2)
    weak = CandidateProfile("excel site supervisor contractors planning", [], 0, 1)
    s, w = score_candidates(job, [strong, weak])
    assert s.total > w.total
    assert s.matched == ["python", "sql", "pandas"] and w.missing == ["python", "sql", "pandas"]
    assert 0 <= w.total <= s.total <= 100
