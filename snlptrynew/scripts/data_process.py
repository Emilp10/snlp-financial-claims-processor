"""Build the FAISS index from raw evidence documents."""
import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

import faiss

from models.embedder import embed_texts

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "evidence_raw"
INDEX_DIR = ROOT / "index"
METADATA_PATH = INDEX_DIR / "metadata.json"
INDEX_PATH = INDEX_DIR / "vector_index.faiss"


def chunk_text(text: str, chunk_size: int = 200, overlap: int = 40) -> List[str]:
    """Simple word-based chunking with optional overlap."""
    words = text.split()
    if not words:
        return []
    step = max(chunk_size - overlap, 1)
    chunks = [
        " ".join(words[i : i + chunk_size])
        for i in range(0, len(words), step)
    ]
    return [chunk.strip() for chunk in chunks if chunk.strip()]


from typing import Tuple


def _parse_header(text: str) -> Tuple[Dict[str, str], str]:
    """Parse simple front-matter style header (key: value) at the top of the file.

    Returns metadata dict and the remaining body text.
    """
    meta: Dict[str, str] = {}
    lines = text.splitlines()
    body_start = 0
    for i, line in enumerate(lines[:20]):  # scan up to 20 lines for headers
        if not line.strip():
            # blank line considered as separator between header and body
            body_start = i + 1
            break
        if ":" in line:
            key, val = line.split(":", 1)
            meta[key.strip().lower()] = val.strip()
            body_start = i + 1
        else:
            # Not a key-value line; stop header parsing
            break
    body = "\n".join(lines[body_start:]).strip()
    return meta, body


def load_documents(chunk_size: int, overlap: int) -> List[dict]:
    """Load raw documents from disk and return chunked records with metadata."""
    records: List[dict] = []
    for file in sorted(RAW_DIR.glob("*.txt")):
        raw = file.read_text(encoding="utf-8").strip()
        if not raw:
            continue
        meta, text = _parse_header(raw)
        if not text:
            continue
        chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        for idx, chunk in enumerate(chunks):
            records.append(
                {
                    "source": meta.get("source", file.name),
                    "title": meta.get("title"),
                    "publish_date": meta.get("date") or meta.get("publish_date"),
                    "url": meta.get("url"),
                    "chunk_index": idx,
                    "text": chunk,
                }
            )
    return records


def build_index(chunk_size: int = 200, overlap: int = 40) -> None:
    """Read evidence, compute embeddings, and build the FAISS index."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    docs = load_documents(chunk_size=chunk_size, overlap=overlap)
    if not docs:
        raise RuntimeError(f"No .txt files found in {RAW_DIR}")

    embeddings = embed_texts(
        [doc["text"] for doc in docs],
        normalize=True,
    )
    dim = embeddings.shape[1]

    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    faiss.write_index(index, str(INDEX_PATH))
    METADATA_PATH.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Indexed {len(docs)} chunks with dimension {dim}.")
    print(f"Index saved to {INDEX_PATH}")
    print(f"Metadata saved to {METADATA_PATH}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the FAISS evidence index.")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=200,
        help="Number of words per chunk before overlap is applied.",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=40,
        help="Number of word overlaps between consecutive chunks.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_index(chunk_size=args.chunk_size, overlap=args.overlap)


if __name__ == "__main__":
    main()
