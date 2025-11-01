"""Thin wrapper to build FAISS index using existing data_process logic.

Usage:
  python scripts\process_and_index.py --chunk-size 250 --overlap 50
"""
from __future__ import annotations

import argparse

# Import the function by module path
from scripts.data_process import build_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunk, embed and index evidence corpus")
    parser.add_argument("--chunk-size", type=int, default=220)
    parser.add_argument("--overlap", type=int, default=40)
    args = parser.parse_args()

    build_index(chunk_size=args.chunk_size, overlap=args.overlap)


if __name__ == "__main__":
    main()
