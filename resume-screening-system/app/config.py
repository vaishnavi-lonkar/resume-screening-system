import os
from dataclasses import dataclass


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./resume_screening.db")
    max_upload_bytes: int = int(float(os.getenv("MAX_UPLOAD_MB", "5")) * 1024 * 1024)
    use_transformers: bool = _bool("USE_TRANSFORMERS")
    transformer_model: str = os.getenv("TRANSFORMER_MODEL", "all-MiniLM-L6-v2")
    w_skills: float = float(os.getenv("WEIGHT_SKILLS", "0.45"))
    w_text: float = float(os.getenv("WEIGHT_TEXT", "0.30"))
    w_experience: float = float(os.getenv("WEIGHT_EXPERIENCE", "0.15"))
    w_education: float = float(os.getenv("WEIGHT_EDUCATION", "0.10"))
    # Cosine similarity at which the text score saturates at 100%.
    text_similarity_ceiling: float = 0.55


settings = Settings()
