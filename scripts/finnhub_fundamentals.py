"""Pulls basic fundamentals and profiles from Finnhub for a list of symbols.

Outputs JSON files under data/fundamentals/{SYMBOL}/.
Requires FINNHUB_API_KEY in environment.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import List

import requests
from dotenv import load_dotenv

OUT_DIR = Path("data/fundamentals")
SYMBOLS_FILE = Path("data/symbols.txt")


def get_symbols() -> List[str]:
    if SYMBOLS_FILE.exists():
        syms = [s.strip().upper() for s in SYMBOLS_FILE.read_text(encoding='utf-8').splitlines() if s.strip() and not s.strip().startswith('#')]
        if syms:
            return syms
    # default set
    return ["AAPL", "MSFT", "TSLA", "NVDA", "AMZN", "GOOGL", "META", "AMD", "INTC"]


def fetch_json(url: str, params: dict) -> dict:
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def main() -> None:
    load_dotenv()
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        raise SystemExit("FINNHUB_API_KEY not set")

    base = "https://finnhub.io/api/v1"
    symbols = get_symbols()
    for sym in symbols:
        try:
            out_sym = OUT_DIR / sym
            # Company profile
            profile = fetch_json(f"{base}/stock/profile2", {"symbol": sym, "token": api_key})
            save_json(out_sym / "profile.json", profile)
            time.sleep(0.2)
            # Basic metrics
            metric = fetch_json(f"{base}/stock/metric", {"symbol": sym, "metric": "all", "token": api_key})
            save_json(out_sym / "metric.json", metric)
            time.sleep(0.2)
            # Financials reported (recent)
            fin = fetch_json(f"{base}/stock/financials-reported", {"symbol": sym, "token": api_key})
            save_json(out_sym / "financials_reported.json", fin)
            time.sleep(0.2)
            # Earnings calendar (limited)
            earn = fetch_json(f"{base}/calendar/earnings", {"symbol": sym, "token": api_key})
            save_json(out_sym / "earnings_calendar.json", earn)
            time.sleep(0.2)
            print(f"Saved fundamentals for {sym}")
        except Exception as err:
            print("[SKIP]", sym, err)
    print(f"Done. Output in {OUT_DIR}")


if __name__ == '__main__':
    main()
