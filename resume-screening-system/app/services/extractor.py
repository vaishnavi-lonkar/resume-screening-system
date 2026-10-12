"""Rule-based information extraction from resume / job-description text."""
import datetime as dt
import re

from .skills import extract_skills

SECTION_HEADINGS = {
    "education": {"education", "academic background", "academic qualifications", "qualifications", "academics"},
    "experience": {"experience", "work experience", "professional experience", "employment history",
                   "internships", "internship experience", "work history", "internship"},
    "skills": {"skills", "technical skills", "key skills", "core competencies", "technologies", "tech stack"},
    "projects": {"projects", "academic projects", "personal projects", "key projects"},
    "certifications": {"certifications", "certificates", "licenses & certifications", "courses", "training",
                       "certifications & courses"},
    "summary": {"summary", "profile", "objective", "about me", "career objective", "professional summary"},
}
_HEADING_LOOKUP = {h: sec for sec, hs in SECTION_HEADINGS.items() for h in hs}

# (level, label, case-insensitive words, case-sensitive abbreviations)
DEGREES = [
    (4, "PhD", r"ph\.?\s?d|doctorate|doctor of philosophy", r"\bPhD\b"),
    (3, "Master's", r"master'?s?|post[- ]?graduate|m\.?\s?tech|mba|mca",
     r"\b(?:M\.?Tech|M\.?E\.?|M\.?Sc\.?|MS|M\.?S\.|MBA|MCA)\b"),
    (2, "Bachelor's", r"bachelor'?s?|b\.?\s?tech|undergraduate|b\.?\s?sc|bca|bba",
     r"\b(?:B\.?Tech|B\.?E\.?|B\.?Sc\.?|BS|B\.?S\.|BCA|BBA|B\.?Com|B\.?A\.)(?!\w)"),
    (1, "Diploma", r"diploma|associate degree", r"\bDiploma\b"),
]
_DEGREE_RES = [(lvl, lab, re.compile(w, re.I), re.compile(a)) for lvl, lab, w, a in DEGREES]
EDU_LABELS = {0: "Not found", 1: "Diploma", 2: "Bachelor's", 3: "Master's", 4: "PhD"}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?<!\d)(\+?\d[\d\s().-]{8,16}\d)(?!\d)")
LINK_RE = re.compile(r"(?:https?://)?(?:www\.)?(?:linkedin\.com|github\.com)/[\w\-./%]+", re.I)
BULLET_RE = re.compile(r"^\s*[•\-\*▪●◦·]\s*")

MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
_DATE = rf"(?:(?:{MONTHS})[a-z]*\.?,?\s+)?(?:19|20)\d{{2}}"
RANGE_RE = re.compile(rf"({_DATE})\s*(?:-|–|—|to)\s*({_DATE}|present|current|now|ongoing|till date)", re.I)
EXPLICIT_YEARS_RE = re.compile(
    r"(\d{1,2}(?:\.\d)?)\s*\+?\s*(?:years?|yrs?)\b[^.\n]{0,40}?experience", re.I)
ANY_YEARS_RE = re.compile(r"(\d{1,2}(?:\.\d)?)\s*\+?\s*(?:years?|yrs?)\b", re.I)


def split_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for line in text.splitlines():
        key = re.sub(r"[^a-z& ]", "", line.lower()).strip()
        if line.strip() and len(line.strip()) < 40 and key in _HEADING_LOOKUP:
            current = _HEADING_LOOKUP[key]
            sections.setdefault(current, [])
            continue
        sections[current].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}


def _lines(block: str, limit: int, max_len: int = 160) -> list[str]:
    out = []
    for raw in block.splitlines():
        line = BULLET_RE.sub("", raw).strip(" \t|")
        if 3 <= len(line) <= max_len and line not in out:
            out.append(line)
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------- contact
def extract_name(text: str, email: str | None, filename: str) -> str:
    skip = {"resume", "curriculum vitae", "cv", "biodata"}
    for line in [l.strip() for l in text.splitlines() if l.strip()][:6]:
        tokens = line.replace(",", " ").split()
        if (1 < len(tokens) <= 4 and line.lower() not in skip
                and all(re.fullmatch(r"[A-Za-z][A-Za-z.'\-]*", t) for t in tokens)
                and line.lower() not in _HEADING_LOOKUP):
            return " ".join(t.capitalize() if t.isupper() else t for t in tokens)
    if email:
        return re.sub(r"[._\d]+", " ", email.split("@")[0]).strip().title() or "Unknown"
    return re.sub(r"[_\-]+", " ", filename.rsplit(".", 1)[0]).title()


def extract_phone(text: str) -> str | None:
    for m in PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group(1))
        if 10 <= len(digits) <= 13:
            return m.group(1).strip()
    return None


# ------------------------------------------------------------- experience
def _to_month_index(token: str, end: bool) -> int:
    token = token.lower().strip()
    if token in {"present", "current", "now", "ongoing", "till date"}:
        today = dt.date.today()
        return today.year * 12 + today.month - 1
    year = int(re.search(r"(?:19|20)\d{2}", token).group())
    m = re.match(rf"({MONTHS})", token)
    names = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    if m:
        month = names.index(m.group(1)[:3])
    else:
        month = 11 if end else 0
    return year * 12 + month


def years_from_ranges(text: str) -> float:
    spans = []
    for a, b in RANGE_RE.findall(text):
        start, end = _to_month_index(a, False), _to_month_index(b, True)
        if end >= start and end - start <= 12 * 40:
            spans.append((start, end + 1))
    spans.sort()
    total, cur_end = 0, None
    cur_start = None
    for s, e in spans:
        if cur_end is None or s > cur_end:
            if cur_end is not None:
                total += cur_end - cur_start
            cur_start, cur_end = s, e
        else:
            cur_end = max(cur_end, e)
    if cur_end is not None:
        total += cur_end - cur_start
    return round(total / 12, 1)


def extract_experience_years(text: str, sections: dict[str, str]) -> float:
    explicit = [float(x) for x in EXPLICIT_YEARS_RE.findall(text)]
    if "experience" in sections:
        body = sections["experience"]
    else:
        body = "\n".join(v for k, v in sections.items()
                         if k not in {"education", "projects", "certifications"})
    computed = years_from_ranges(body)
    return round(max([computed] + explicit), 1)


def extract_required_years(jd: str) -> float | None:
    m = EXPLICIT_YEARS_RE.search(jd) or ANY_YEARS_RE.search(jd)
    return float(m.group(1)) if m else None


# -------------------------------------------------------------- education
def education_level(text: str) -> int:
    best = 0
    for lvl, _, words, abbr in _DEGREE_RES:
        if words.search(text) or abbr.search(text):
            best = max(best, lvl)
    return best


def extract_education(text: str, sections: dict[str, str]) -> tuple[list[str], int]:
    block = sections.get("education") or text
    entries = []
    for line in _lines(block, 40, 200):
        if education_level(line) or re.search(r"university|college|institute|school of", line, re.I):
            entries.append(line)
    return entries[:5], education_level(block)


def extract_required_education(jd: str) -> int:
    lvl = education_level(jd)
    if lvl:
        return lvl
    if re.search(r"\bdegree\b", jd, re.I):
        return 2
    return 0


# ---------------------------------------------------- certifications etc.
def extract_certifications(text: str, sections: dict[str, str]) -> list[str]:
    certs = _lines(sections.get("certifications", ""), 10)
    for line in _lines(text, 400, 150):
        if re.search(r"\bcertif(?:ied|ication|icate)\b", line, re.I) and line not in certs:
            certs.append(line)
    return certs[:10]


def extract_projects(sections: dict[str, str]) -> list[str]:
    block = sections.get("projects", "")
    titles = [BULLET_RE.sub("", l).strip() for l in block.splitlines()
              if l.strip() and not BULLET_RE.match(l) and len(l.strip()) <= 110]
    return (titles or _lines(block, 8, 160))[:8]


# ------------------------------------------------------------ entry point
def parse_resume(text: str, filename: str) -> dict:
    sections = split_sections(text)
    email_m = EMAIL_RE.search(text)
    email = email_m.group().lower() if email_m else None
    education, level = extract_education(text, sections)
    return {
        "name": extract_name(text, email, filename),
        "email": email,
        "phone": extract_phone(text),
        "links": sorted({m.group() for m in LINK_RE.finditer(text)})[:4],
        "skills": extract_skills(text),
        "education": education,
        "education_level": level,
        "experience_years": extract_experience_years(text, sections),
        "certifications": extract_certifications(text, sections),
        "projects": extract_projects(sections),
    }
