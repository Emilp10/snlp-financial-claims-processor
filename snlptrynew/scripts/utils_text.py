import re
from pathlib import Path

_slug_re = re.compile(r"[^a-z0-9]+")


def slugify(text: str, max_len: int = 80) -> str:
    text = text.lower().strip()
    text = _slug_re.sub("-", text)
    text = text.strip("-")
    if len(text) > max_len:
        text = text[:max_len].rstrip("-")
    return text or "doc"


def unique_path(base_dir: Path, base_name: str, ext: str = ".txt") -> Path:
    base = base_dir / f"{base_name}{ext}"
    if not base.exists():
        return base
    i = 2
    while True:
        p = base_dir / f"{base_name}-{i}{ext}"
        if not p.exists():
            return p
        i += 1
