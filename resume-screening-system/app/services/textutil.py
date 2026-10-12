import re
import unicodedata

_URL = re.compile(r"https?://\S+|www\.\S+", re.I)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def normalize(text: str) -> str:
    """Unicode-normalise, strip control chars, tidy whitespace but keep line breaks."""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\u200b\ufeff]", "", text)
    text = text.replace("\u2022", "•").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_for_matching(text: str) -> str:
    """Flatten text for similarity analysis: lowercase, no URLs/emails, no stray symbols."""
    text = _URL.sub(" ", text)
    text = _EMAIL.sub(" ", text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9+#./\s-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()
