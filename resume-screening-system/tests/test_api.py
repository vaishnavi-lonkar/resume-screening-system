import io

from docx import Document


def _job(client, sample):
    r = client.post("/api/jobs", json={"title": "Data Scientist", "description": sample("job_description.txt")})
    assert r.status_code == 201
    return r.json()


def test_job_requirements_extracted(client, sample):
    job = _job(client, sample)
    assert {"python", "sql", "pandas", "scikit-learn"} <= set(job["required_skills"])
    assert job["min_experience_years"] == 1.0 and job["min_education_level"] == 2


def test_screen_and_rank(client, sample):
    job = _job(client, sample)
    docx = io.BytesIO()
    d = Document()
    for line in sample("resume_priya_sharma.txt").splitlines():
        d.add_paragraph(line)
    d.save(docx)
    files = [
        ("files", ("rahul.txt", sample("resume_rahul_verma.txt").encode(), "text/plain")),
        ("files", ("priya.docx", docx.getvalue(), "application/octet-stream")),
        ("files", ("ananya.txt", sample("resume_ananya_iyer.txt").encode(), "text/plain")),
        ("files", ("bad.exe", b"MZ....", "application/octet-stream")),
    ]
    r = client.post(f"/api/jobs/{job['id']}/screen", files=files)
    assert r.status_code == 200
    body = r.json()
    names = [x["name"] for x in body["results"]]
    assert names[-1] == "Rahul Verma" and set(names[:2]) == {"Priya Sharma", "Ananya Iyer"}
    assert [x["rank"] for x in body["results"]] == [1, 2, 3]
    assert body["errors"][0]["filename"] == "bad.exe"

    # same resume again is not duplicated
    again = client.post(f"/api/jobs/{job['id']}/screen",
                        files=[("files", ("copy.txt", sample("resume_rahul_verma.txt").encode(), "text/plain"))])
    assert len(again.json()["results"]) == 3

    csv = client.get(f"/api/jobs/{job['id']}/results.csv")
    assert csv.status_code == 200 and csv.text.splitlines()[0].startswith("rank,name")

    cid = body["results"][-1]["candidate_id"]
    assert client.delete(f"/api/candidates/{cid}").status_code == 204
    assert len(client.get(f"/api/jobs/{job['id']}/results").json()) == 2


def test_validation_and_404(client):
    assert client.post("/api/jobs", json={"title": "x", "description": "short"}).status_code == 422
    assert client.get("/api/jobs/9999").status_code == 404
