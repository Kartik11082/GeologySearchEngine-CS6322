"""Single-pass clustering: assign each term to a cluster by cosine similarity to centroid."""

from __future__ import annotations

from corpus import sparse_cosine, term_tfidf_vector


def build_scalar_clusters(
    ordered_terms: list[str],
    inverted_index: dict[str, dict[str, int]],
    N: int,
    *,
    cosine_threshold: float,
    max_cluster_size: int,
) -> dict[str, int]:
    """
    Single-pass: assign each term to the cluster whose centroid has highest cosine
    with the term, if above threshold; else start a new cluster.
    Returns term -> stable cluster_id (int).
    """
    centroids: list[dict[str, float]] = []
    sizes: list[int] = []
    cluster_label: list[int] = []
    term_to_cluster: dict[str, int] = {}
    next_label = 0

    for t in ordered_terms:
        v = term_tfidf_vector(t, inverted_index, N)
        if not v:
            term_to_cluster[t] = -1
            continue

        best_j = -1
        best_sim = -1.0
        for j, cent in enumerate(centroids):
            if sizes[j] >= max_cluster_size:
                continue
            sim = sparse_cosine(v, cent)
            if sim > best_sim:
                best_sim = sim
                best_j = j

        if best_j < 0 or best_sim < cosine_threshold:
            centroids.append(dict(v))
            sizes.append(1)
            cluster_label.append(next_label)
            term_to_cluster[t] = next_label
            next_label += 1
        else:
            n = sizes[best_j]
            old = centroids[best_j]
            new_cent: dict[str, float] = {}
            for d in set(old) | set(v):
                new_cent[d] = (old.get(d, 0.0) * n + v.get(d, 0.0)) / (n + 1.0)
            centroids[best_j] = new_cent
            sizes[best_j] = n + 1
            term_to_cluster[t] = cluster_label[best_j]

    return term_to_cluster


def cluster_members_scalar(term_to_cluster: dict[str, int]) -> dict[int, list[str]]:
    m: dict[int, list[str]] = {}
    for t, cid in term_to_cluster.items():
        if cid < 0:
            continue
        m.setdefault(cid, []).append(t)
    return m


def expand_scalar(
    query_terms: list[str],
    term_to_cluster: dict[str, int],
    members: dict[int, list[str]],
    *,
    sibling_terms: int,
    max_total: int = 16,
) -> list[str]:
    qset = set(query_terms)
    out: list[str] = []
    seen: set[str] = set()
    for t in query_terms:
        cid = term_to_cluster.get(t, -1)
        if cid < 0:
            continue
        pool = sorted(u for u in members.get(cid, []) if u not in qset and u not in seen)
        for u in pool[:sibling_terms]:
            seen.add(u)
            out.append(u)
            if len(out) >= max_total:
                return out
    return out
