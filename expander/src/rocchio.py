"""Rocchio pseudo-relevance feedback (v1: top-N terms from modified vector, then BM25)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from tfidf_utils import tfidf_weight


def _centroid_vector(
    doc_ids: set[str],
    inverted_index: dict[str, dict[str, int]],
    N: int,
) -> dict[str, float]:
    """Average TF-IDF vector over documents (sparse: term -> weight)."""
    if not doc_ids:
        return {}
    acc: dict[str, float] = defaultdict(float)
    n = len(doc_ids)
    for term, posting in inverted_index.items():
        s = 0.0
        for d in doc_ids:
            if d in posting:
                tf = posting[d]
                s += tfidf_weight(tf, len(posting), N)
        if s != 0.0:
            acc[term] = s / n
    return dict(acc)


def _query_vector(
    query_terms: list[str],
    inverted_index: dict[str, dict[str, int]],
    N: int,
) -> dict[str, float]:
    q: dict[str, float] = {}
    for term in query_terms:
        posting = inverted_index.get(term)
        if not posting:
            continue
        q[term] = tfidf_weight(1, len(posting), N)
    return q


def _rocchio_modified_vector(
    q_vec: dict[str, float],
    rel_cent: dict[str, float],
    nr_cent: dict[str, float],
    alpha: float,
    beta: float,
    gamma: float,
    clip_negatives: bool,
) -> dict[str, float]:
    terms: set[str] = set(q_vec) | set(rel_cent) | set(nr_cent)
    out: dict[str, float] = {}
    for t in terms:
        v = (
            alpha * q_vec.get(t, 0.0)
            + beta * rel_cent.get(t, 0.0)
            - gamma * nr_cent.get(t, 0.0)
        )
        if clip_negatives and v < 0.0:
            v = 0.0
        if v != 0.0:
            out[t] = v
    return out


def expand_rocchio(
    query_terms: list[str],
    inverted_index: dict[str, dict[str, int]],
    N: int,
    ranked_doc_ids: list[str],
    *,
    alpha: float,
    beta: float,
    gamma: float,
    pseudo_relevant_k: int,
    pseudo_nonrelevant_k: int,
    expansion_terms: int,
    clip_negatives: bool,
) -> list[str]:
    """
    Return list of new terms (stems) to append to the query, excluding originals.
    """
    if not query_terms:
        return []

    qset = set(query_terms)
    pool = ranked_doc_ids
    if len(pool) < pseudo_relevant_k + 1:
        return []

    rel = set(pool[:pseudo_relevant_k])
    nr: set[str] = set()
    if pseudo_nonrelevant_k > 0 and len(pool) >= pseudo_relevant_k + pseudo_nonrelevant_k + 2:
        nr = set(pool[-pseudo_nonrelevant_k:])

    q_vec = _query_vector(query_terms, inverted_index, N)
    rel_cent = _centroid_vector(rel, inverted_index, N)
    nr_cent = _centroid_vector(nr, inverted_index, N) if nr else {}

    g = gamma if nr else 0.0
    mod = _rocchio_modified_vector(
        q_vec, rel_cent, nr_cent, alpha, beta, g, clip_negatives
    )

    candidates = [(t, w) for t, w in mod.items() if t not in qset]
    candidates.sort(key=lambda x: x[1], reverse=True)
    return [t for t, _ in candidates[:expansion_terms]]
