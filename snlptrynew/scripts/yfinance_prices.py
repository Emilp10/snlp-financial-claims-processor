"""Download recent OHLCV price data using yfinance for a set of symbols.

Outputs CSV under data/market/{SYMBOL}.csv
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import yfinance as yf

OUT_DIR = Path("data/market")
SYMBOLS_FILE = Path("data/symbols.txt")


def get_symbols() -> List[str]:
    if SYMBOLS_FILE.exists():
        syms = [s.strip().upper() for s in SYMBOLS_FILE.read_text(encoding='utf-8').splitlines() if s.strip() and not s.strip().startswith('#')]
        if syms:
            return syms
    return ["AAPL", "MSFT", "TSLA", "NVDA", "AMZN", "GOOGL", "META", "AMD", "INTC"]


def main() -> None:
    syms = get_symbols()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    end = datetime.today()
    start = end - timedelta(days=365)
    for sym in syms:
        try:
            df = yf.download(sym, start=start.date(), end=end.date(), progress=False, auto_adjust=True)
            if df is None or df.empty:
                print("[SKIP] no data for", sym)
                continue
            path = OUT_DIR / f"{sym}.csv"
            df.to_csv(path)
            print("Saved", path)
        except Exception as err:
            print("[SKIP]", sym, err)


if __name__ == '__main__':
    main()
