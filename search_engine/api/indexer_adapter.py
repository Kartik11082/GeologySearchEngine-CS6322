"""
Indexer-backed relevance adapter for the FastAPI integration layer.

Only X2 (indexing/relevance) functionality is integrated here.
X4 (clustering) and X5 (query expansion) are intentionally not implemented.
"""

from __future__ import annotations

import sys
import threading
from collections import defaultdict
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_INDEXER_SRC = _PROJECT_ROOT / "indexer" / "src"

_ENGINE: Any = None
_ENGINE_LOCK = threading.Lock()


def _ensure_engine():
    """Load and cache the indexer SearchEngine instance."""
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    with _ENGINE_LOCK:
        if _ENGINE is not None:
            return _ENGINE

        if str(_INDEXER_SRC) not in sys.path:
            sys.path.insert(0, str(_INDEXER_SRC))

        from search import SearchEngine  # type: ignore

        engine = SearchEngine()
        try:
            engine.load()
        except FileNotFoundError:
            # Build from crawler batches if prebuilt artifacts are missing.
            engine.build()

        _ENGINE = engine
        return _ENGINE


def _normalize_scores(results: list[dict[str, Any]]) -> dict[int, float]:
    max_score = max((float(r.get("score", 0.0)) for r in results), default=0.0)
    if max_score <= 0:
        return {int(r["doc_id"]): 0.0 for r in results if "doc_id" in r}

    norm: dict[int, float] = {}
    for row in results:
        if "doc_id" not in row:
            continue
        norm[int(row["doc_id"])] = float(row.get("score", 0.0)) / max_score
    return norm


def _ensemble_search(query: str, top_k: int) -> list[dict[str, Any]]:
    """
    Combine real indexer relevance methods into one hybrid ranking.

    This is still based entirely on indexer outputs (no synthetic documents).
    """
    engine = _ensure_engine()
    fetch_k = max(top_k * 4, 30)

    tfidf = engine.search(query, method="tfidf", top_k=fetch_k)
    pagerank = engine.search(query, method="pagerank", top_k=fetch_k)
    hits = engine.search(query, method="hits", top_k=fetch_k)

    weights = {
        "tfidf": 0.50,
        "pagerank": 0.30,
        "hits": 0.20,
    }

    score_maps = {
        "tfidf": _normalize_scores(tfidf),
        "pagerank": _normalize_scores(pagerank),
        "hits": _normalize_scores(hits),
    }

    doc_lookup: dict[int, dict[str, Any]] = {}
    merged: defaultdict[int, float] = defaultdict(float)

    for docs in (tfidf, pagerank, hits):
        for doc in docs:
            if "doc_id" not in doc:
                continue
            doc_lookup[int(doc["doc_id"])] = doc

    for method, score_map in score_maps.items():
        weight = weights[method]
        for doc_id, norm_score in score_map.items():
            merged[doc_id] += weight * norm_score

    ranked_ids = sorted(merged.items(), key=lambda x: x[1], reverse=True)[:top_k]
    output: list[dict[str, Any]] = []

    for rank, (doc_id, score) in enumerate(ranked_ids, start=1):
        base = dict(doc_lookup.get(doc_id, {}))
        base["doc_id"] = doc_id
        base["rank"] = rank
        base["score"] = round(float(score), 6)
        output.append(base)

    return output


def search_relevance(query: str, model: str = "vector", top_k: int = 10) -> dict[str, Any]:
    """
    Search real indexer data and return:
    { "source": model, "documents": [...] }.
    """
    model = (model or "vector").strip().lower()
    engine = _ensure_engine()

    if model == "vector":
        docs = engine.search(query, method="tfidf", top_k=top_k)
    elif model == "pagerank":
        docs = engine.search(query, method="pagerank", top_k=top_k)
    elif model == "hits":
        docs = engine.search(query, method="hits", top_k=top_k)
    elif model == "combined":
        docs = _ensemble_search(query, top_k=top_k)
    else:
        docs = engine.search(query, method="tfidf", top_k=top_k)

    return {"source": model, "documents": docs}
