"""Online retrieval helpers for hybrid RAG fallback.

This module provides lightweight, optional online search when local evidence is
insufficient. It fetches recent finance articles via:
- NewsAPI (if NEWS_API_KEY is set)
- RSS feeds listed under data/feeds/*.txt (Reuters/AP and others)
and extracts full text using newspaper3k where possible.

It returns evidence items shaped like EvidenceChunk to be merged with local results.
All network calls are best-effort and time-boxed; if nothing can be fetched, an empty
list is returned without raising.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Optional

import json
import re

import feedparser
import httpx
from app.config import get_settings
from models.embedder import embed_text, embed_texts


@dataclass
class Article:
    title: str
    url: str
    source: str
    published: Optional[str]
    text: str


def _allowed(url: str, allow_domains_regex: re.Pattern[str]) -> bool:
    try:
        host = re.sub(r"^https?://", "", url).split("/")[0]
    except Exception:
        return False
    return bool(allow_domains_regex.search(host))


async def _newsapi_search(
    client: httpx.AsyncClient, query: str, days: int, max_items: int, keywords: Optional[List[str]] = None
) -> List[Article]:
    settings = get_settings()
    if not settings.news_api_key:
        return []

    to_date = datetime.utcnow().date()
    from_date = to_date - timedelta(days=days)
    q = " ".join(keywords) if keywords else query
    params = {
        "q": q,
        "from": str(from_date),
        "to": str(to_date),
        "language": "en",
        "sortBy": "relevancy",
        "pageSize": min(max_items, 50),
        "apiKey": settings.news_api_key,
    }
    try:
        resp = await client.get("https://newsapi.org/v2/everything", params=params, timeout=settings.online_timeout_s)
        data = resp.json()
        articles = []
        for a in data.get("articles", [])[:max_items]:
            title = a.get("title") or ""
            url = a.get("url") or ""
            source = (a.get("source") or {}).get("name") or "NewsAPI"
            published = a.get("publishedAt")
            # Prefer full content if available; fallback to description
            text = (a.get("content") or a.get("description") or "").strip()
            if title and url:
                articles.append(Article(title=title, url=url, source=source, published=published, text=text))
        return articles
    except Exception:
        return []


def _load_feeds() -> List[str]:
    feed_files = [
        Path("data/feeds/rss_feeds.txt"),
        Path("data/feeds/press_releases.txt"),
    ]
    feeds: List[str] = []
    for f in feed_files:
        if f.exists():
            try:
                for line in f.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        feeds.append(line)
            except Exception:
                continue
    return feeds


def _rss_fetch(max_items: int) -> List[Article]:
    feeds = _load_feeds()
    items: List[Article] = []
    for url in feeds:
        try:
            parsed = feedparser.parse(url)
            for e in parsed.entries[: max(0, max_items // max(1, len(feeds)) + 1)]:
                title = getattr(e, "title", "") or ""
                link = getattr(e, "link", "") or ""
                published = getattr(e, "published", None)
                source = re.sub(r"^https?://", "", parsed.href).split("/")[0] if getattr(parsed, "href", None) else "rss"
                summary = getattr(e, "summary", "") or ""
                if title and link:
                    items.append(Article(title=title, url=link, source=source, published=published, text=summary))
        except Exception:
            continue
    return items[:max_items]


def _fetch_full_text_sync(url: str, timeout: float) -> str:
    # Leave as best-effort to avoid blocking on heavy parsing
    try:
        from newspaper import Article as NPArticle

        a = NPArticle(url=url)
        a.download()
        a.parse()
        return (a.text or "").strip()
    except Exception:
        return ""


def _rank_by_similarity(query: str, articles: List[Article], top_k: int, allow_domains_regex: re.Pattern[str]) -> List[dict]:
    # Filter by allowlist
    filtered = [a for a in articles if _allowed(a.url, allow_domains_regex)]
    if not filtered:
        return []

    texts: List[str] = []
    for a in filtered:
        body = a.text
        if not body:
            body = _fetch_full_text_sync(a.url, get_settings().online_timeout_s)
        # Build a compact text payload
        payload = f"{a.title}\n\n{body}".strip()
        texts.append(payload)

    if not texts:
        return []

    # Compute similarities
    q = embed_text(query, normalize=True)
    embs = embed_texts(texts, normalize=True)
    # cosine since embeddings are normalized
    import numpy as np

    scores = (embs @ q).tolist()
    ranked = sorted(zip(filtered, texts, scores), key=lambda t: t[2], reverse=True)[:top_k]
    out: List[dict] = []
    for art, payload, score in ranked:
        out.append(
            {
                "text": payload,
                "source": art.source or "online",
                "chunk_index": None,
                "score": float(score),
                "url": art.url,
                "title": art.title,
                "published": art.published,
            }
        )
    return out


async def fetch_online_evidence(
    query: str,
    days: Optional[int] = None,
    max_articles: Optional[int] = None,
    keywords: Optional[List[str]] = None,
) -> List[dict]:
    """Fetch and rank online articles for a query.

    Returns a list of evidence-like dicts with optional url/title fields.
    """
    settings = get_settings()
    days = days or settings.online_days
    max_articles = max_articles or (settings.online_top_k * 4)
    allow_re = re.compile(settings.online_allow_domains or ".*", re.IGNORECASE)

    async with httpx.AsyncClient(headers={"User-Agent": "StudentResearchBot/1.0"}) as client:
        newsapi_items = await _newsapi_search(client, query, days=days, max_items=max_articles, keywords=keywords)

    rss_items = _rss_fetch(max_articles)
    articles = newsapi_items + rss_items
    if not articles:
        return []

    ranked = _rank_by_similarity(query, articles, top_k=settings.online_top_k, allow_domains_regex=allow_re)
    return ranked
