"""Ingest Reuters/AP and other news via RSS feeds into data/evidence_raw/.

Reads feed URLs from data/feeds/rss_feeds.txt (one per line, # comments ok).
Attempts to fetch full article HTML and extract text; falls back to summary.
"""
from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

SAVE_DIR = Path("data/evidence_raw")
FEED_FILE = Path("data/feeds/rss_feeds.txt")
HEADERS = {"User-Agent": os.getenv("NEWS_USER_AGENT", "StudentResearchBot/1.0 (contact@example.com)")}

DEFAULT_FEEDS = [
    # Reuters Markets/US and Business
    "https://www.reuters.com/markets/us/rss",
    "https://www.reuters.com/finance/markets/rss",
    # AP Business (note: availability of RSS may vary)
    "https://apnews.com/hub/ap-top-news?utm_source=apnews.com&utm_medium=referral&utm_campaign=apnews_rss&utm_content=business&output=rss",
]


def safe_name(url: str, prefix: str = "rss") -> str:
    h = hashlib.md5(url.encode()).hexdigest()[:10]
    dom = urlparse(url).netloc.replace("www.", "").replace(".", "_")
    return f"{prefix}_{dom}_{h}.txt"


def extract_text_from_url(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        return ""
    soup = BeautifulSoup(r.text, "lxml")
    text = soup.get_text("\n").strip()
    return text


def save_entry(entry, source_name: str) -> Path | None:
    url = entry.link
    title = getattr(entry, "title", "Untitled")
    date = getattr(entry, "published", "")

    text = extract_text_from_url(url)
    # Fallback to summary if full text is too short
    if len(text.split()) < 60:
        summary = getattr(entry, "summary", "")
        if summary:
            text = summary
    if len(text.split()) < 40:
        return None

    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    header = (
        f"title: {title}\n"
        f"source: {source_name}\n"
        f"date: {date}\n"
        f"url: {url}\n\n"
    )
    path = SAVE_DIR / safe_name(url)
    path.write_text(header + text, encoding="utf-8")
    return path


def main() -> None:
    load_dotenv()
    if FEED_FILE.exists():
        feeds = [line.strip() for line in FEED_FILE.read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith('#')]
    else:
        feeds = DEFAULT_FEEDS

    saved = 0
    for feed in feeds:
        try:
            d = feedparser.parse(feed)
            source = urlparse(feed).netloc
            for e in d.entries[:20]:
                try:
                    p = save_entry(e, source)
                    if p:
                        saved += 1
                    time.sleep(0.2)
                except Exception as inner_err:
                    print("[SKIP] entry", inner_err)
        except Exception as err:
            print("[SKIP] feed", feed, err)
    print(f"Saved {saved} RSS items to {SAVE_DIR}")


if __name__ == "__main__":
    main()
