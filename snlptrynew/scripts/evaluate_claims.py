"""Evaluate the pipeline on a claims CSV by calling the FastAPI backend.

Usage:
  uvicorn app.main:app --reload  # in a separate terminal
  python scripts\evaluate_claims.py --file data\claims\claims.csv --top-k 5

Outputs simple accuracy and dumps per-claim results.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from typing import List

import requests

API_URL = "http://127.0.0.1:8000/check"


def load_claims(path: str) -> List[dict]:
    rows: List[dict] = []
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if row.get("claim_text"):
                rows.append(row)
    return rows


def evaluate(path: str, sleep: float = 0.2) -> None:
    claims = load_claims(path)
    n = len(claims)
    correct = 0
    results = []
    for i, c in enumerate(claims, 1):
        claim_text = c["claim_text"].strip()
        expected = (c.get("label") or "").strip()
        try:
            resp = requests.post(API_URL, json={"text": claim_text}, timeout=90)
            resp.raise_for_status()
            data = resp.json()
            got = data.get("result", {}).get("verdict", "")
            results.append({"claim": claim_text, "expected": expected, "got": got, "raw": data})
            if expected and got and expected.lower() == got.lower():
                correct += 1
        except Exception as e:
            results.append({"claim": claim_text, "error": str(e)})
        time.sleep(sleep)

    acc = (correct / n) if n else 0.0
    print(f"Claims evaluated: {n}")
    print(f"Accuracy (exact verdict match): {acc:.2%}")

    with open("data/eval_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("Saved detailed results to data/eval_results.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate claims via backend")
    parser.add_argument("--file", default="data/claims/claims.csv")
    args = parser.parse_args()
    evaluate(args.file)


if __name__ == "__main__":
    main()
