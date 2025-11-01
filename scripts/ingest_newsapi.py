"""Ingest business news via NewsAPI into data/evidence_raw/ as normalized .txt files.

Usage:
  python scripts/ingest_newsapi.py --query tesla --page-size 20

Requires env var NEWS_API_KEY. Respects rate limits. By default saves sources we
consider reputable; optionally target explicit `--sources` or `--domains`.
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Optional

import requests
from dotenv import load_dotenv

from scripts.utils_text import slugify, unique_path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "evidence_raw"

REPUTABLE_SOURCES = {
    "reuters",
    "associated-press",
    "the-wall-street-journal",
    "bloomberg",
    "financial-times",
}


def is_reputable(source_name: Optional[str], allow_any: bool = False, allow_list: Optional[List[str]] = None) -> bool:
    if not source_name:
        return False
    s = source_name.lower()
    if allow_any:
        return True
    if allow_list:
        return any(src.strip().lower() in s for src in allow_list)
    return any(key in s for key in REPUTABLE_SOURCES)


def fetch_newsapi(api_key: str, query: str, page_size: int = 20, days: int = 7, sources: Optional[List[str]] = None, domains: Optional[List[str]] = None) -> List[dict]:
    url = "https://newsapi.org/v2/everything"
    from_dt = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "from": from_dt,
        "apiKey": api_key,
    }
    if sources:
        params["sources"] = ",".join(sources)
    if domains:
        params["domains"] = ",".join(domains)
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("articles", [])


def save_article(article: dict, allow_any: bool = False, allow_list: Optional[List[str]] = None) -> Optional[Path]:
    title = article.get("title") or "Untitled"
    source = (article.get("source") or {}).get("name") or "Unknown"
    url = article.get("url") or ""
    published_at = article.get("publishedAt") or ""
    description = article.get("description") or ""
    content = article.get("content") or ""

    if not is_reputable(source, allow_any=allow_any, allow_list=allow_list):
        return None

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    base_name = slugify(f"{source}-{title}")
    path = unique_path(RAW_DIR, base_name)

    header = [
        f"title: {title}",
        f"source: {source}",
        f"date: {published_at[:10]}",
        f"url: {url}",
        "",
    ]
    body = description.strip()
    if content and content not in description:
        body = (body + "\n\n" + content.strip()).strip()

    path.write_text("\n".join(header) + body + "\n", encoding="utf-8")
    return path


def main() -> None:
    # Load .env for NEWS_API_KEY if present
    load_dotenv()
    parser = argparse.ArgumentParser(description="Ingest NewsAPI articles")
    parser.add_argument("--query", default="finance OR earnings OR acquisition")
    parser.add_argument("--page-size", type=int, default=25)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--sources", type=str, default="", help="Comma-separated NewsAPI source ids to target (e.g., reuters,associated-press)")
    parser.add_argument("--domains", type=str, default="", help="Comma-separated domains to target (e.g., reuters.com,apnews.com)")
    args = parser.parse_args()

    api_key = os.getenv("NEWS_API_KEY")
    if not api_key:
        raise SystemExit("NEWS_API_KEY not set in environment")

    sources = [s for s in args.sources.split(",") if s.strip()] or None
    domains = [d for d in args.domains.split(",") if d.strip()] or None

    articles = fetch_newsapi(api_key, query=args.query, page_size=args.page_size, days=args.days, sources=sources, domains=domains)
    saved = 0
    for art in articles:
        # If explicit sources/domains used, allow any; otherwise apply default reputable filter
        p = save_article(art, allow_any=bool(sources or domains), allow_list=sources)
        if p:
            saved += 1
    print(f"Saved {saved} articles to {RAW_DIR}")


if __name__ == "__main__":
    main()
