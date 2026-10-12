from app.services.extractor import parse_resume, extract_required_years, years_from_ranges
from app.services.skills import extract_skills


def test_skill_boundaries():
    s = extract_skills("Worked with JavaScript, C++, node.js and Python3. No java experience here? Java yes.")
    assert {"javascript", "c++", "node.js", "python", "java"} <= set(s)
    assert "c" not in s
    assert "java" not in extract_skills("JavaScript only")


def test_parse_priya(sample):
    p = parse_resume(sample("resume_priya_sharma.txt"), "p.txt")
    assert p["name"] == "Priya Sharma"
    assert p["email"] == "priya.sharma@example.com"
    assert p["phone"].startswith("+91")
    assert p["education_level"] == 2
    assert {"python", "sql", "scikit-learn", "power bi"} <= set(p["skills"])
    assert p["experience_years"] >= 2.5
    assert any("Google Data Analytics" in c for c in p["certifications"])
    assert "Resume Classifier" in p["projects"]


def test_masters_detected(sample):
    assert parse_resume(sample("resume_ananya_iyer.txt"), "a.txt")["education_level"] == 3


def test_overlapping_ranges_not_double_counted():
    assert years_from_ranges("Jan 2020 - Dec 2021 and Jun 2021 - Dec 2022") == 3.0


def test_required_years():
    assert extract_required_years("We need 3+ years of experience in ML") == 3.0
    assert extract_required_years("No requirement") is None
