# Fake Financial News Checker (Local RAG)

This project implements a Retrieval-Augmented Generation (RAG) system to verify financial news claims. Evidence and retrieval run locally, while reasoning leverages an OpenAI large language model. The backend exposes a FastAPI service, and the frontend is a Next.js app.

## Features

- Local FAISS vector index for semantic search over trusted financial evidence.
- Sentence Transformers for text embeddings (runs entirely on your machine).
- FastAPI backend that orchestrates retrieval and LLM reasoning.
- Next.js frontend for submitting claims and inspecting the verdict with citations.
- Extensible data ingestion and evaluation utilities.

## Directory Structure

```
rag_fake_news_checker/
├── app/                  # FastAPI application modules
├── data/                 # Source evidence, processed artifacts
├── frontend/             # Next.js client application
├── index/                # FAISS index + metadata (generated)
├── models/               # Embedding utilities
├── scripts/              # Data processing helpers
├── requirements.txt      # Python dependencies
└── README.md             # Project guide
```

## Quickstart

### 1. Prepare Python Environment

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Populate Evidence

Add trustworthy financial articles or filings as `.txt` files under `data/evidence_raw/`. Each file should contain the article body. Include metadata (title, source, date, URL) at the top if available.

You can also auto-ingest news and filings:

```bash
# NewsAPI (requires NEWS_API_KEY in .env)
python scripts/ingest_newsapi.py --query "finance OR earnings OR acquisition" --page-size 25 --days 7

# Finnhub company news (requires FINNHUB_API_KEY)
python scripts/ingest_finnhub.py --symbols TSLA,AAPL,MSFT --days 14

# SEC filings via public JSON endpoints (set SEC_USER_AGENT in .env)
python scripts/sec_fetch.py --tickers TSLA,AAPL,MSFT,NVDA --per-ticker 2

# Curated URL fetch (reads data/urls.txt if present)
python scripts/news_fetch.py --urls-file data/urls.txt

# Company IR/press releases via RSS feeds (reads data/feeds/press_releases.txt)
python scripts/press_release_fetch.py

# Reuters/AP and other finance feeds via RSS (reads data/feeds/rss_feeds.txt)
python scripts/ingest_reuters_rss.py

# NewsAPI with explicit sources/domains (if your plan allows)
python scripts/ingest_newsapi.py --query "earnings OR acquisition OR guidance" --sources reuters,associated-press --page-size 50 --days 14
# or target domains (fallback if sources are restricted)
python scripts/ingest_newsapi.py --query "earnings OR acquisition OR guidance" --domains reuters.com,apnews.com,wsj.com,bloomberg.com --page-size 50 --days 14

# Pull company fundamentals from Finnhub (requires FINNHUB_API_KEY)
python scripts/finnhub_fundamentals.py

# Pull recent OHLCV prices (1y) for symbols in data/symbols.txt
python scripts/yfinance_prices.py
```

### 3. Build the Vector Index

```bash
# Either call the wrapper (same effect)
python scripts/process_and_index.py --chunk-size 250 --overlap 50

# Or call the original builder
python scripts/data_process.py --chunk-size 250 --overlap 50
```

This script chunks documents, generates embeddings, and saves the index to `index/vector_index.faiss` with metadata in `index/metadata.json`. Header lines like `title:`, `source:`, `date:`, and `url:` are parsed and stored in metadata for better provenance.

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```
OPENAI_API_KEY=sk-...
OPENAI_CHAT_MODEL=gpt-4o-mini
EMBEDDING_MODEL=all-MiniLM-L6-v2
TOP_K=5

# Ingestion keys (optional)
NEWS_API_KEY=...
FINNHUB_API_KEY=...

# Polite user agent for web/RSS fetching
NEWS_USER_AGENT=StudentResearchBot/1.0 (contact@example.com)
```

### 5. Run the Backend

```bash
uvicorn app.main:app --reload
```

The FastAPI docs will be available at <http://127.0.0.1:8000/docs>.

### 6. Run the Next.js Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000> and submit financial claims for verification.

### 7. Optional: Evaluate on a claims dataset

```bash
# Backend should be running
python scripts/evaluate_claims.py --file data/claims/claims.csv
```

This prints an accuracy figure and saves per-claim results to `data/eval_results.json`.

### 8. Build a better ground truth set

- Generate claim candidates from your current evidence titles:

```
python scripts/claims_seed_from_metadata.py
```

This writes `data/claims/candidates.csv` for quick human labeling. Start by labeling a few dozen claims spanning companies, sources (Reuters/AP/SEC/IR), and topics (earnings, guidance, M&A). Then point the evaluator at your labeled CSV.

## Testing the Pipeline

1. Use the FastAPI docs to issue a `POST /check` request with `{"text": "Your claim"}`.
2. From the frontend, enter a headline or statement and review the verdict.

## Optional Enhancements

- Swap in a higher-quality embedding model (e.g., `multi-qa-MiniLM-L6-cos-v1`).
- Add URL ingestion using `newspaper3k`.
- Cache verdicts in SQLite or other lightweight stores.
- Add evaluation scripts to benchmark retrieval and reasoning performance.
- Replace the OpenAI API with a local LLM server (Ollama, llama.cpp, etc.).

## License

This project is provided as-is for educational purposes. Ensure compliance with the terms of any third-party datasets or APIs that you use during deployment.
