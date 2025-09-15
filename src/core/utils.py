# utils.py
import re
import unicodedata

def _strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore")
    return text.decode("utf-8")

def normalize_leave_type(leave_type: str) -> str:
    if not leave_type: return ""
    cleaned = _strip_accents(str(leave_type)).casefold().strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if "sin goce" in cleaned: return "permiso sin goce de sueldo"
    return cleaned