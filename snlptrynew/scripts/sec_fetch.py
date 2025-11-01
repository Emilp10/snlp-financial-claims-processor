"""Fetch selected SEC filings via public SEC JSON endpoints and save as normalized .txt.

Usage:
  python scripts\sec_fetch.py --tickers TSLA,AAPL,MSFT --per-ticker 2

Notes:
- Provide a descriptive User-Agent per SEC fair use policy.
- Saves files with lowercase header keys (title/source/date/url) for parser compatibility.
"""
from __future__ import annotations

import argparse
import os
import re
import time
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

SAVE_DIR = "data/evidence_raw"
BASE = "https://data.sec.gov"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
TARGET_FORMS = {"10-K", "10-Q", "8-K", "8-K/A", "425", "SC TO-T", "S-4"}


def get_user_agent() -> str:
    ua = os.getenv("SEC_USER_AGENT") or os.getenv("NEWS_USER_AGENT")
    if not ua:
        # Fallback placeholder (please set SEC_USER_AGENT in .env to your email/contact)
        ua = "StudentResearchBot/1.0 (contact@example.com)"
    return ua


def get_ticker_map(ua: str) -> Dict[str, str]:
    r = requests.get(TICKERS_URL, headers={"User-Agent": ua}, timeout=30)
    r.raise_for_status()
    data = r.json()
    return {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in data.values()}


def get_submissions(cik: str, ua: str) -> dict:
    url = f"{BASE}/submissions/CIK{cik}.json"
    r = requests.get(url, headers={"User-Agent": ua}, timeout=30)
    r.raise_for_status()
    return r.json()


def clean_text(html_or_txt: str) -> str:
    soup = BeautifulSoup(html_or_txt, "lxml")
    text = soup.get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_primary_doc(cik: str, accession_no: str, primary_doc: str, ua: str) -> Optional[str]:
    acc_nodash = accession_no.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_nodash}/{primary_doc}"
    r = requests.get(url, headers={"User-Agent": ua}, timeout=60)
    if r.status_code != 200:
        return None
    return r.text


def save_file(meta: Dict[str, str], content: str) -> str:
    os.makedirs(SAVE_DIR, exist_ok=True)
    safe_ticker = meta.get("ticker", "NA")
    filename = f"sec_{safe_ticker}_{meta['form']}_{meta['date']}_{meta['acc']}.txt".replace("/", "-")
    path = os.path.join(SAVE_DIR, filename)
    header = (
        f"title: {meta.get('title','SEC Filing')}\n"
        f"source: SEC EDGAR\n"
        f"date: {meta['date']}\n"
        f"url: {meta['url']}\n"
        f"ticker: {meta.get('ticker','')}\n"
        f"form: {meta['form']}\n\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + content)
    return path


def main() -> None:
    # Load .env so SEC_USER_AGENT and other keys are available
    load_dotenv()
    parser = argparse.ArgumentParser(description="Fetch SEC filings for selected tickers")
    parser.add_argument("--tickers", default="TSLA,AAPL,MSFT,NVDA,META,AMZN,GOOGL,JPM,BAC,INTC")
    parser.add_argument("--per-ticker", type=int, default=2)
    args = parser.parse_args()

    ua = get_user_agent()
    tmap = get_ticker_map(ua)
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]

    total_saved = 0
    for tk in tickers:
        cik = tmap.get(tk)
        if not cik:
            print(f"[WARN] Ticker not found in SEC map: {tk}")
            continue
        subs = get_submissions(cik, ua)
        filings = subs.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        accs = filings.get("accessionNumber", [])
        prim = filings.get("primaryDocument", [])
        dates = filings.get("filingDate", [])
        count = 0
        for form, acc, pd, dt in zip(forms, accs, prim, dates):
            if form not in TARGET_FORMS:
                continue
            doc = fetch_primary_doc(cik, acc, pd, ua)
            if not doc:
                continue
            url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-','')}/{pd}"
            text = clean_text(doc)
            meta = {
                "title": f"{tk} {form} filing",
                "date": dt,
                "url": url,
                "form": form,
                "acc": acc,
                "ticker": tk,
            }
            save_file(meta, text)
            total_saved += 1
            count += 1
            time.sleep(0.3)  # polite delay
            if count >= args.per_ticker:
                break

    print(f"Saved {total_saved} SEC filings to {SAVE_DIR}")


if __name__ == "__main__":
    main()
