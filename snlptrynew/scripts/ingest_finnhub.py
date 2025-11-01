"""Ingest company news via Finnhub into data/evidence_raw/.

Usage:
  python scripts/ingest_finnhub.py --symbols TSLA,AAPL,MSFT --days 14

Requires FINNHUB_API_KEY in environment.
"""
from __future__ import annotations

import argparse
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import requests
from dotenv import load_dotenv

from scripts.utils_text import slugify, unique_path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "evidence_raw"

DEFAULT_SYMBOLS = [
    "TSLA",
    "AAPL",
    "MSFT",
    "NVDA",
    "META",
    "AMZN",
    "GOOGL",
    "JPM",
    "HDB",   # HDFC Bank ADR
    "ADANIENT.NS",  # Adani Enterprises on NSE for illustration
]
SYMBOLS_FILE_DEFAULT = ROOT / "data" / "symbols.txt"


def daterange(days: int) -> Tuple[str, str]:
    to_d = date.today()
    from_d = to_d - timedelta(days=days)
    return from_d.isoformat(), to_d.isoformat()


def fetch_company_news(api_key: str, symbol: str, frm: str, to: str) -> List[dict]:
    url = "https://finnhub.io/api/v1/company-news"
    params = {"symbol": symbol, "from": frm, "to": to, "token": api_key}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json() or []


def save_item(item: dict, symbol: str) -> Optional[Path]:
    source = item.get("source") or "Finnhub"
    headline = item.get("headline") or "Untitled"
    datetime_ts = item.get("datetime")
    url = item.get("url") or ""
    summary = item.get("summary") or ""
    date_str = ""
    if isinstance(datetime_ts, (int, float)) and datetime_ts:
        try:
            from datetime import datetime
            date_str = datetime.utcfromtimestamp(int(datetime_ts)).strftime("%Y-%m-%d")
        except Exception:
            date_str = ""

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    base_name = slugify(f"{symbol}-{source}-{headline}")
    path = unique_path(RAW_DIR, base_name)

    header = [
        f"title: {headline}",
        f"source: {source}",
        f"date: {date_str}",
        f"url: {url}",
        "",
    ]
    body = summary.strip()

    # Skip if too little content
    if len(body) < 40:
        return None

    path.write_text("\n".join(header) + body + "\n", encoding="utf-8")
    return path


def load_symbols(arg_symbols: str, symbols_file: Optional[Path]) -> List[str]:
    if symbols_file and symbols_file.exists():
        syms = [s.strip() for s in symbols_file.read_text(encoding="utf-8").splitlines() if s.strip() and not s.strip().startswith('#')]
        if syms:
            return syms
    if arg_symbols:
        return [s.strip() for s in arg_symbols.split(",") if s.strip()]
    return DEFAULT_SYMBOLS


def main() -> None:
    # Load .env for FINNHUB_API_KEY if present
    load_dotenv()
    parser = argparse.ArgumentParser(description="Ingest Finnhub company news")
    parser.add_argument("--symbols", default="", help="Comma-separated symbols. If omitted, uses data/symbols.txt or defaults")
    parser.add_argument("--symbols-file", type=str, default=str(SYMBOLS_FILE_DEFAULT), help="Path to a symbols.txt file")
    parser.add_argument("--days", type=int, default=14)
    args = parser.parse_args()

    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        raise SystemExit("FINNHUB_API_KEY not set in environment")

    frm, to = daterange(args.days)
    symbols = load_symbols(args.symbols, Path(args.symbols_file) if args.symbols_file else None)
    saved = 0
    for sym in symbols:
        items = fetch_company_news(api_key, sym, frm, to)
        for it in items:
            p = save_item(it, sym)
            if p:
                saved += 1
    print(f"Saved {saved} Finnhub items to {RAW_DIR}")


if __name__ == "__main__":
    main()
