"""Association-based expansion via co-occurrence / Jaccard in shared documents."""

from __future__ import annotations


def expand_association(
    query_terms: list[str],
    inverted_index: dict[str, dict[str, int]],
    doc_terms: dict[str, set[str]],
    df: dict[str, int],
    *,
    top_m: int,
    max_total_terms: int,
) -> list[str]:
    """
    For each query term, rank co-occurring terms by Jaccard in document space.
    Returns deduplicated new terms (stems), highest score first, capped at max_total_terms.
    """
    if not query_terms:
        return []

    qset = set(query_terms)
    scores: dict[str, float] = {}

    for t in query_terms:
        posting = inverted_index.get(t)
        if not posting:
            continue
        df_t = len(posting)
        docs_t = set(posting.keys())
        cand_counts: dict[str, int] = {}
        for d in docs_t:
            for u in doc_terms.get(d, ()):
                if u == t or u in qset:
                    continue
                cand_counts[u] = cand_counts.get(u, 0) + 1

        for u, co_uv in cand_counts.items():
            df_u = df.get(u, 0)
            if df_u <= 0:
                continue
            union = df_t + df_u - co_uv
            if union <= 0:
                continue
            jacc = co_uv / union
            prev = scores.get(u, 0.0)
            if jacc > prev:
                scores[u] = jacc

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    out: list[str] = []
    for u, _ in ranked:
        if u in qset:
            continue
        out.append(u)
        if len(out) >= max_total_terms:
            break
    return out
