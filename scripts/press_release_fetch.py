"""Fetch latest items from company IR/PR RSS feeds and save as normalized .txt.

Usage:
  python scripts\press_release_fetch.py

Provide feed URLs in data/feeds/press_releases.txt (one per line). If the file
is missing, a default set of AAPL/TSLA/NVDA + SEC press releases will be used.
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
HEADERS = {"User-Agent": os.getenv("NEWS_USER_AGENT", "StudentResearchBot/1.0 (contact@example.com)")}
FEED_FILE = Path("data/feeds/press_releases.txt")

DEFAULT_FEEDS = [
    # Company IR feeds
    "https://ir.apple.com/rss/news-releases.xml",
    "https://ir.tesla.com/press-releases/rss.xml",
    "https://investor.nvidia.com/rss/news-releases.xml",
    "https://investor.microsoft.com/rss/news-releases.xml",
    "https://www.amd.com/en/rss/press-releases.xml",
    "https://investor.amazon.com/rss/news-releases.xml",
    "https://abc.xyz/investor/rss/news.xml",
    # SEC press releases
    "https://www.sec.gov/news/pressreleases.rss",
]


def safe_name(url: str, prefix: str = "pr") -> str:
    h = hashlib.md5(url.encode()).hexdigest()[:10]
    dom = urlparse(url).netloc.replace("www.", "").replace(".", "_")
    return f"{prefix}_{dom}_{h}.txt"


def fetch_and_save(entry, source_name: str) -> Path | None:
    url = entry.link
    r = requests.get(url, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, "lxml")
    text = soup.get_text("\n").strip()
    if len(text.split()) < 60:
        return None

    title = entry.title
    date = getattr(entry, "published", "")

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
    # Load .env for NEWS_USER_AGENT or future keys
    load_dotenv()
    saved = 0
    # Load feed list from file or fall back to defaults
    if FEED_FILE.exists():
        feeds = [line.strip() for line in FEED_FILE.read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#")]
    else:
        feeds = DEFAULT_FEEDS

    for feed in feeds:
        d = feedparser.parse(feed)
        source = urlparse(feed).netloc
        for e in d.entries[:5]:  # top 5 per feed
            try:
                p = fetch_and_save(e, source)
                if p:
                    saved += 1
                time.sleep(0.3)
            except Exception as err:
                print("[SKIP]", err)
    print(f"Saved {saved} press releases to {SAVE_DIR}")


if __name__ == "__main__":
    main()
