"""Convert the sample .txt resumes into .docx files for trying the upload flow."""
from pathlib import Path

from docx import Document

folder = Path(__file__).resolve().parent.parent / "sample_data"
for txt in folder.glob("resume_*.txt"):
    doc = Document()
    for line in txt.read_text().splitlines():
        doc.add_paragraph(line)
    doc.save(txt.with_suffix(".docx"))
    print("wrote", txt.with_suffix(".docx").name)
