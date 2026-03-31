"""Metric (cosine) term clusters via union-find on within-document term pairs."""

from __future__ import annotations

import random

from corpus import sparse_cosine, term_tfidf_vector


class UnionFind:
    def __init__(self, n: int) -> None:
        self.p = list(range(n))
        self.r = [0] * n

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.r[ra] < self.r[rb]:
            ra, rb = rb, ra
        self.p[rb] = ra
        if self.r[ra] == self.r[rb]:
            self.r[ra] += 1


def build_metric_clusters(
    pruned_terms: list[str],
    term_to_idx: dict[str, int],
    inverted_index: dict[str, dict[str, int]],
    doc_terms: dict[str, set[str]],
    N: int,
    *,
    sim_threshold: float,
    max_terms_per_doc: int,
    rng: random.Random | None = None,
) -> dict[str, int]:
    """
    Map term -> cluster root id (as int index of some representative term).
    """
    rng = rng or random.Random(0)
    V = len(pruned_terms)
    uf = UnionFind(V)
    # Cache term vectors for pruned vocabulary (memory: O(V * avg posting))
    vec_cache: dict[str, dict[str, float]] = {}

    def vec(t: str) -> dict[str, float]:
        if t not in vec_cache:
            vec_cache[t] = term_tfidf_vector(t, inverted_index, N)
        return vec_cache[t]

    for _doc_id, terms in doc_terms.items():
        pts = [t for t in terms if t in term_to_idx]
        if len(pts) > max_terms_per_doc:
            pts = rng.sample(pts, max_terms_per_doc)
        L = len(pts)
        for i in range(L):
            ti = pts[i]
            vi = vec(ti)
            if not vi:
                continue
            for j in range(i + 1, L):
                tj = pts[j]
                vj = vec(tj)
                if not vj:
                    continue
                if sparse_cosine(vi, vj) >= sim_threshold:
                    uf.union(term_to_idx[ti], term_to_idx[tj])

    root_of: dict[str, int] = {}
    for t in pruned_terms:
        idx = term_to_idx[t]
        r = uf.find(idx)
        root_of[t] = r
    return root_of


def cluster_members(
    root_of: dict[str, int],
) -> dict[int, list[str]]:
    members: dict[int, list[str]] = {}
    for t, r in root_of.items():
        members.setdefault(r, []).append(t)
    return members


def expand_metric(
    query_terms: list[str],
    root_of: dict[str, int],
    members: dict[int, list[str]],
    *,
    sibling_terms: int,
    max_total: int = 16,
) -> list[str]:
    qset = set(query_terms)
    out: list[str] = []
    seen: set[str] = set()
    for t in query_terms:
        if t not in root_of:
            continue
        r = root_of[t]
        pool = sorted(u for u in members.get(r, []) if u not in qset and u not in seen)
        for u in pool[:sibling_terms]:
            seen.add(u)
            out.append(u)
            if len(out) >= max_total:
                return out
    return out
