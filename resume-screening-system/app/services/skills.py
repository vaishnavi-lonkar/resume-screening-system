"""Skill taxonomy and matching. Extend TAXONOMY to teach the system new skills."""
import re
from functools import lru_cache

# canonical name -> aliases (all matched case-insensitively on word boundaries)
TAXONOMY: dict[str, list[str]] = {
    # Languages
    "python": ["python3"], "java": [], "javascript": ["js", "ecmascript"], "typescript": ["ts"],
    "c++": ["cpp"], "c#": ["csharp", "c sharp"], "c": ["c programming", "c language"],
    "go": ["golang"], "rust": [], "kotlin": [], "swift": [], "php": [], "ruby": [],
    "r": ["r programming", "r language", "rstudio"], "scala": [], "matlab": [],
    "bash": ["shell scripting", "shell script"], "sql": [],
    # Data / ML
    "machine learning": ["ml"], "deep learning": ["dl"], "nlp": ["natural language processing"],
    "computer vision": ["opencv"], "data analysis": ["data analytics", "exploratory data analysis", "eda"],
    "data science": [], "data visualization": ["data visualisation"], "statistics": ["statistical analysis"],
    "feature engineering": [], "time series": ["time series analysis", "forecasting"],
    "pandas": [], "numpy": [], "scipy": [], "scikit-learn": ["sklearn", "scikit learn"],
    "tensorflow": [], "keras": [], "pytorch": ["torch"], "xgboost": [], "lightgbm": [],
    "hugging face": ["huggingface", "transformers"], "spacy": [], "nltk": [],
    "llm": ["large language models", "large language model", "llms"], "generative ai": ["genai", "gen ai"],
    "matplotlib": [], "seaborn": [], "plotly": [], "power bi": ["powerbi"], "tableau": [],
    "excel": ["microsoft excel", "ms excel"], "a/b testing": ["ab testing", "a/b test"],
    # Data engineering / DB
    "mysql": [], "postgresql": ["postgres"], "mongodb": ["mongo"], "sqlite": [], "redis": [],
    "elasticsearch": [], "oracle": [], "nosql": [], "spark": ["pyspark", "apache spark"],
    "hadoop": [], "kafka": ["apache kafka"], "airflow": ["apache airflow"], "etl": ["data pipelines", "data pipeline"],
    "snowflake": [], "bigquery": [], "dbt": [], "data warehousing": ["data warehouse"],
    # Web / backend
    "fastapi": [], "flask": [], "django": [], "node.js": ["nodejs", "node js"], "express": ["express.js", "expressjs"],
    "spring boot": ["springboot", "spring"], "react": ["react.js", "reactjs"], "angular": ["angularjs"],
    "vue": ["vue.js", "vuejs"], "next.js": ["nextjs"], "html": ["html5"], "css": ["css3"],
    "tailwind": ["tailwind css"], "bootstrap": [], "rest api": ["rest apis", "restful api", "restful apis", "rest"],
    "graphql": [], "microservices": [], ".net": ["dotnet", "asp.net"],
    # Cloud / DevOps
    "aws": ["amazon web services"], "azure": ["microsoft azure"], "gcp": ["google cloud", "google cloud platform"],
    "docker": [], "kubernetes": ["k8s"], "terraform": [], "jenkins": [], "ci/cd": ["cicd", "ci cd"],
    "git": [], "github": [], "gitlab": [], "linux": [], "mlops": [], "devops": [],
    # Other
    "agile": ["scrum"], "jira": [], "unit testing": ["pytest", "junit", "unittest"], "selenium": [],
    "android": [], "flutter": [], "react native": [], "cybersecurity": ["information security"],
    "communication": ["communication skills"], "leadership": [], "problem solving": ["problem-solving"],
    "teamwork": ["team work", "collaboration"],
}

_BOUNDARY_L = r"(?<![\w+#.])"
_BOUNDARY_R = r"(?![\w+#])"


@lru_cache(maxsize=2048)
def _pattern(term: str) -> re.Pattern:
    return re.compile(_BOUNDARY_L + re.escape(term.lower()) + _BOUNDARY_R, re.IGNORECASE)


def contains_term(text: str, term: str) -> bool:
    return bool(_pattern(term).search(text))


@lru_cache(maxsize=1)
def _alias_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for canon, aliases in TAXONOMY.items():
        index[canon] = canon
        for a in aliases:
            index[a.lower()] = canon
    return index


def canonical(skill: str) -> str:
    s = skill.strip().lower()
    return _alias_index().get(s, s)


def extract_skills(text: str) -> list[str]:
    """Return canonical skills found in text, in taxonomy order."""
    found = []
    for term, canon in _alias_index().items():
        if canon not in found and contains_term(text, term):
            found.append(canon)
    return sorted(found)
