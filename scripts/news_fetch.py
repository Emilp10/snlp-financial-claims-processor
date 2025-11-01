"""Fetch articles from a curated URL list using newspaper3k and save as normalized .txt.

Usage:
  python scripts\news_fetch.py --urls-file data\urls.txt

If --urls-file is omitted, uses the hardcoded URLS list below. Saves lowercase header keys for parser compatibility.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
from urllib.parse import urlparse

from newspaper import Article
from dotenv import load_dotenv

SAVE_DIR = Path("data/evidence_raw")

# Starter list; prefer reputable and accessible sources
URLS = [
    "https://www.reuters.com/markets/asia/india-markets-close-higher-2025-10-21/",
    "https://www.reuters.com/technology/tesla-q3-earnings-2025-10-21/",
    "https://www.investopedia.com/terms/c/cpi.asp",
]


def safe_name(url: str) -> str:
    h = hashlib.md5(url.encode()).hexdigest()[:10]
    dom = urlparse(url).netloc.replace("www.", "").replace(".", "_")
    return f"news_{dom}_{h}.txt"


def save_article(url: str) -> Path:
    a = Article(url)
    a.download()
    a.parse()
    title = a.title or "Untitled"
    text = a.text or ""
    # a.publish_date is not always present
    date = a.publish_date.isoformat() if getattr(a, "publish_date", None) else ""
    src = urlparse(url).netloc

    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    header = (
        f"title: {title}\n"
        f"source: {src}\n"
        f"date: {date}\n"
        f"url: {url}\n\n"
    )
    path = SAVE_DIR / safe_name(url)
    path.write_text(header + text, encoding="utf-8")
    return path


def main() -> None:
    # Load .env (not strictly needed here but keeps consistency for USER_AGENT or future keys)
    load_dotenv()
    parser = argparse.ArgumentParser(description="Fetch curated URLs and save to evidence_raw")
    parser.add_argument("--urls-file", default="")
    args = parser.parse_args()

    urls = list(URLS)
    if args.urls_file:
        uf = Path(args.urls_file)
        if uf.exists():
            urls.extend([ln.strip() for ln in uf.read_text(encoding="utf-8").splitlines() if ln.strip()])

    saved = 0
    for u in urls:
        try:
            save_article(u)
            saved += 1
        except Exception as e:  # network or parsing issues
            print("[SKIP]", u, e)
    print(f"Saved {saved} articles to {SAVE_DIR}")


if __name__ == "__main__":
    main()
