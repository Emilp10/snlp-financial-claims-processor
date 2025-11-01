"""Generate unlabeled claim candidates from existing metadata titles.

Reads index/metadata.json and produces data/claims/candidates.csv with fields:
  claim_id, claim_text, source, publish_date, url
Intended for human labeling to build a high-quality ground-truth set.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

META = Path("index/metadata.json")
OUT = Path("data/claims/candidates.csv")


def main() -> None:
    if not META.exists():
        raise SystemExit("metadata.json not found; build index first")
    data = json.loads(META.read_text(encoding="utf-8"))
    # Collapse by URL+title to avoid duplicates across chunks
    seen = set()
    rows = []
    for d in data:
        title = (d.get("title") or "").strip()
        url = (d.get("url") or "").strip()
        key = (title, url)
        if not title or key in seen:
            continue
        seen.add(key)
        rows.append({
            "claim_id": f"U{len(rows)+1:04d}",
            "claim_text": title,
            "source": d.get("source") or "",
            "publish_date": d.get("publish_date") or "",
            "url": url,
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["claim_id", "claim_text", "source", "publish_date", "url"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} candidate claims to {OUT}")


if __name__ == '__main__':
    main()
