"""Relevance models: TF-IDF cosine similarity and Okapi BM25."""

import math
from typing import Any

from config import BM25_B, BM25_K1
from preprocessor import preprocess


# ═══════════════════════════════════════════════════════════════════
#  Model 1 — TF-IDF with cosine similarity
# ═══════════════════════════════════════════════════════════════════


def _tfidf_weight(tf: int, df: int, N: int) -> float:
    """Log-weighted TF × IDF."""
    if tf <= 0 or df <= 0:
        return 0.0
    return (1.0 + math.log10(tf)) * math.log10(N / df)


def rank_tfidf(
    query: str,
    inverted_index: dict[str, dict[str, int]],
    doc_store: dict[str, dict],
    N: int,
    top_k: int = 10,
) -> list[tuple[str, float]]:
    """
    Rank documents by TF-IDF cosine similarity to the query.

    Returns a sorted list of (doc_id, score) descending by score.
    """
    query_terms = preprocess(query)
    if not query_terms:
        return []

    # ── query vector weights ──────────────────────────────────────
    query_weights: dict[str, float] = {}
    for term in query_terms:
        posting = inverted_index.get(term)
        if posting is None:
            continue
        df = len(posting)
        query_weights[term] = _tfidf_weight(1, df, N)

    if not query_weights:
        return []

    # ── accumulate document scores ────────────────────────────────
    scores: dict[str, float] = {}
    doc_norms: dict[str, float] = {}

    for term, q_w in query_weights.items():
        posting = inverted_index[term]
        for doc_id, tf in posting.items():
            d_w = _tfidf_weight(tf, len(posting), N)
            scores[doc_id] = scores.get(doc_id, 0.0) + q_w * d_w
            doc_norms[doc_id] = doc_norms.get(doc_id, 0.0) + d_w * d_w

    # ── normalise by document vector magnitude ────────────────────
    query_norm = math.sqrt(sum(w * w for w in query_weights.values()))
    for doc_id in scores:
        d_norm = math.sqrt(doc_norms.get(doc_id, 1.0))
        scores[doc_id] /= (query_norm * d_norm) if (query_norm * d_norm) > 0 else 1.0

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:top_k]


# ═══════════════════════════════════════════════════════════════════
#  Model 2 — Okapi BM25
# ═══════════════════════════════════════════════════════════════════


def rank_bm25(
    query: str,
    inverted_index: dict[str, dict[str, int]],
    doc_store: dict[str, dict],
    N: int,
    avg_dl: float,
    top_k: int = 10,
    k1: float = BM25_K1,
    b: float = BM25_B,
) -> list[tuple[str, float]]:
    """
    Rank documents using Okapi BM25.

    Returns a sorted list of (doc_id, score) descending by score.
    """
    query_terms = preprocess(query)
    if not query_terms:
        return []

    scores: dict[str, float] = {}

    for term in query_terms:
        posting = inverted_index.get(term)
        if posting is None:
            continue

        df = len(posting)
        # IDF component (with smoothing to avoid negatives)
        idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)

        for doc_id, tf in posting.items():
            dl = doc_store.get(doc_id, {}).get("doc_len", avg_dl)
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * (dl / avg_dl))
            scores[doc_id] = scores.get(doc_id, 0.0) + idf * (numerator / denominator)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:top_k]
