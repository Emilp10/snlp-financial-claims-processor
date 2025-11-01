"""Lightweight keyword extraction to narrow online news search.

Heuristics:
- Tickers: tokens of 1-5 uppercase letters (e.g., TSLA, AAPL)
- Capitalized terms: Proper-noun-like tokens (Apple, Tesla, Reuters)
- Numeric qualifiers: Q3, 2025, bps, YoY

This avoids heavy dependencies and works reasonably for finance headlines.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List, Set


_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "on",
    "by",
    "for",
    "with",
    "at",
    "from",
    "is",
    "are",
    "was",
    "were",
    "this",
    "that",
    "it",
    "as",
    "about",
}


def _load_symbols() -> Set[str]:
    symbols_file = Path("data/symbols.txt")
    symbols: Set[str] = set()
    if symbols_file.exists():
        try:
            for line in symbols_file.read_text(encoding="utf-8").splitlines():
                s = line.strip().upper()
                if 1 <= len(s) <= 6 and s.isalpha():
                    symbols.add(s)
        except Exception:
            pass
    return symbols


_SYMBOLS = _load_symbols()


def extract_keywords(text: str, max_k: int = 6) -> List[str]:
    text = text or ""
    candidates: List[str] = []

    # Tickers-like uppercase tokens
    for tok in re.findall(r"\b[A-Z]{1,5}\b", text):
        if tok in _SYMBOLS or len(tok) >= 2:
            candidates.append(tok)

    # Capitalized words (proper-noun-like)
    for tok in re.findall(r"\b[A-Z][a-z]{2,}\b", text):
        tl = tok.lower()
        if tl not in _STOPWORDS:
            candidates.append(tok)

    # Finance numeric qualifiers
    for tok in re.findall(r"\b(Q[1-4]|\d{4}|\d+%|bps|YoY|yoy)\b", text, flags=re.IGNORECASE):
        candidates.append(tok)

    # Deduplicate preserving order
    seen: Set[str] = set()
    uniq: List[str] = []
    for c in candidates:
        key = c.upper()
        if key not in seen:
            uniq.append(c)
            seen.add(key)

    return uniq[:max_k]
