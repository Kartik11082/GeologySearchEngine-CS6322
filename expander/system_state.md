# Expander (X5) — system state

Living notes for query expansion. Update when behavior or integration changes.

## Implemented (v1)

- **Retrieval contract:** Expanded query is a single space-separated bag of **stems** (same space as indexer `preprocess`). One `SearchEngine.search(..., method=bm25, top_k=10)` after expansion.
- **Methods:** `rocchio` (pseudo-RF Rocchio + top-N terms), `association` (Jaccard co-occurrence in shared docs), `metric` (cosine union–find clusters on within-doc term pairs, pruned vocab), `scalar` (single-pass cosine-to-centroid clusters, pruned vocab).
- **Integration:** `search_engine/api/expansion_client.py` uses a **singleton** `QueryExpander`. `GET /api/expand?q=&method=` (default `rocchio`). Capabilities advertise expansion + method list.
- **Frontend:** Expansion panel method tabs drive `method` on `/api/expand`.

## Not implemented yet

- Judged Rocchio (qrels-driven Dr/Dnr) — schema reserved in `queries/rocchio_queries.json`.
- Disk-backed expander artifacts (`data/*.npz`, manifest vs indexer hash) — structures built in-memory on first use per process.
- `evaluation.py` / `tuning.py` full pipelines — stubs exit gracefully until query JSON files exist.
- v2 fusion / weighted BM25 query vectors.

## Python environment (conda `nlp`)

Use the **`nlp`** conda environment for this stack (NLTK, NumPy, indexer, FastAPI).

```bash
conda activate nlp
cd GeologySearchEngine-CS6322   # repo root
pip install -r indexer/requirements.txt -r search_engine/requirements.txt
cd search_engine && python main.py
```

Offline scripts (`expander/src/evaluation.py`, `tuning.py`): same env, `cd expander/src && python …`.

## Dependencies

- Indexer on `sys.path`: `SearchEngine`, `preprocess`. Requires built `indexer/data/*` (or crawler batches for auto-build).

## Config

- Defaults in `expander/src/expander_config.py` (Rocchio α/β/γ, k, thresholds, pruning `MIN_DF` / `MAX_DF_RATIO`). Renamed from `config.py` so it never shadows `indexer/src/config.py` when Python’s cwd is `expander/src`.
