"""Corpus-level structures built from the inverted index."""

from __future__ import annotations

from collections import defaultdict

from tfidf_utils import tfidf_weight


def build_doc_terms(inverted_index: dict[str, dict[str, int]]) -> dict[str, set[str]]:
    """doc_id (str) -> set of terms appearing in that document."""
    doc_terms: dict[str, set[str]] = defaultdict(set)
    for term, posting in inverted_index.items():
        for doc_id in posting:
            doc_terms[doc_id].add(term)
    return dict(doc_terms)


def term_df(inverted_index: dict[str, dict[str, int]]) -> dict[str, int]:
    return {t: len(p) for t, p in inverted_index.items()}


def prune_vocab(
    inverted_index: dict[str, dict[str, int]],
    N: int,
    min_df: int,
    max_df_ratio: float,
) -> set[str]:
    """Terms kept for cluster precomputation."""
    max_df = max(1, int(N * max_df_ratio))
    kept: set[str] = set()
    for term, posting in inverted_index.items():
        df = len(posting)
        if df >= min_df and df <= max_df:
            kept.add(term)
    return kept


def term_tfidf_vector(
    term: str,
    inverted_index: dict[str, dict[str, int]],
    N: int,
) -> dict[str, float]:
    """Sparse doc vector for one term: doc_id -> tf-idf weight."""
    posting = inverted_index.get(term)
    if not posting:
        return {}
    df = len(posting)
    out: dict[str, float] = {}
    for doc_id, tf in posting.items():
        out[doc_id] = tfidf_weight(tf, df, N)
    return out


def sparse_dot(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(va * b[d] for d, va in a.items() if d in b)


def sparse_norm(a: dict[str, float]) -> float:
    return sum(v * v for v in a.values()) ** 0.5


def sparse_cosine(a: dict[str, float], b: dict[str, float]) -> float:
    na, nb = sparse_norm(a), sparse_norm(b)
    if na <= 0 or nb <= 0:
        return 0.0
    return sparse_dot(a, b) / (na * nb)
