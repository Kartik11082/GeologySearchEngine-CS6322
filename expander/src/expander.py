"""
Unified query expander: Rocchio, association, metric, and scalar cluster expansion.

v1 contract: expanded query is a space-separated bag of stems passed once to SearchEngine.
"""

from __future__ import annotations

import math
import sys
import threading

import expander_config as cfg

if str(cfg.INDEXER_SRC) not in sys.path:
    sys.path.insert(0, str(cfg.INDEXER_SRC))

from preprocessor import preprocess  # noqa: E402
from search import SearchEngine  # noqa: E402

from association_cluster import expand_association  # noqa: E402
from corpus import build_doc_terms, prune_vocab, term_df  # noqa: E402
from metric_cluster import (  # noqa: E402
    build_metric_clusters,
    cluster_members,
    expand_metric,
)
from rocchio import expand_rocchio  # noqa: E402
from scalar_cluster import (  # noqa: E402
    build_scalar_clusters,
    cluster_members_scalar,
    expand_scalar,
)


class QueryExpander:
    """
    Loads indexer SearchEngine once; lazily builds doc-centric and cluster structures.
    Thread-safe for lazy initialization.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._engine: SearchEngine | None = None
        self._doc_terms: dict[str, set[str]] | None = None
        self._df: dict[str, int] | None = None
        self._metric_root: dict[str, int] | None = None
        self._metric_members: dict[int, list[str]] | None = None
        self._scalar_term_cluster: dict[str, int] | None = None
        self._scalar_members: dict[int, list[str]] | None = None

    def _ensure_engine(self) -> SearchEngine:
        if self._engine is not None:
            return self._engine
        with self._lock:
            if self._engine is None:
                eng = SearchEngine()
                try:
                    eng.load()
                except FileNotFoundError:
                    eng.build()
                self._engine = eng
            return self._engine

    def _ensure_doc_stats(self) -> None:
        if self._doc_terms is not None:
            return
        with self._lock:
            if self._doc_terms is not None:
                return
            eng = self._ensure_engine()
            self._doc_terms = build_doc_terms(eng.inverted_index)
            self._df = term_df(eng.inverted_index)

    def _ensure_metric(self) -> None:
        if self._metric_root is not None:
            return
        self._ensure_doc_stats()
        with self._lock:
            if self._metric_root is not None:
                return
            eng = self._ensure_engine()
            pruned = sorted(
                prune_vocab(
                    eng.inverted_index,
                    eng.N,
                    cfg.MIN_DF,
                    cfg.MAX_DF_RATIO,
                )
            )
            term_to_idx = {t: i for i, t in enumerate(pruned)}
            root = build_metric_clusters(
                pruned,
                term_to_idx,
                eng.inverted_index,
                self._doc_terms,  # type: ignore[arg-type]
                eng.N,
                sim_threshold=cfg.METRIC_SIM_THRESHOLD,
                max_terms_per_doc=cfg.METRIC_MAX_TERMS_PER_DOC,
            )
            members = cluster_members(root)
            self._metric_root = root
            self._metric_members = members

    def _ensure_scalar(self) -> None:
        if self._scalar_term_cluster is not None:
            return
        self._ensure_doc_stats()
        with self._lock:
            if self._scalar_term_cluster is not None:
                return
            eng = self._ensure_engine()
            pruned = sorted(
                prune_vocab(
                    eng.inverted_index,
                    eng.N,
                    cfg.MIN_DF,
                    cfg.MAX_DF_RATIO,
                )
            )
            df_map = self._df  # type: ignore[assignment]
            if cfg.SCALAR_PASS_ORDER == "df_asc":
                pruned.sort(key=lambda t: (df_map.get(t, 0), t))
            else:
                pruned.sort(
                    key=lambda t: (
                        -math.log(eng.N / max(1, df_map.get(t, 1))),
                        t,
                    )
                )

            tc = build_scalar_clusters(
                pruned,
                eng.inverted_index,
                eng.N,
                cosine_threshold=cfg.SCALAR_DOT_THRESHOLD,
                max_cluster_size=cfg.SCALAR_MAX_CLUSTER_SIZE,
            )
            self._scalar_term_cluster = tc
            self._scalar_members = cluster_members_scalar(tc)

    def expand(self, query: str, method: str = "rocchio") -> dict:
        """
        Return dict with keys: original_query, expanded_query, method, documents.
        documents match indexer SearchEngine.search format.
        """
        method = (method or "rocchio").strip().lower()
        if method not in cfg.VALID_METHODS:
            method = "rocchio"

        eng = self._ensure_engine()
        q_terms = preprocess(query)
        if not q_terms:
            return {
                "original_query": query.strip(),
                "expanded_query": query.strip(),
                "method": method,
                "documents": [],
            }

        original_joined = " ".join(q_terms)
        added: list[str] = []

        if method == "rocchio":
            pool_k = max(
                cfg.ROCCHIO_FETCH_POOL,
                cfg.ROCCHIO_PSEUDO_RELEVANT_K + cfg.ROCCHIO_PSEUDO_NONRELEVANT_K + 5,
            )
            ranked = eng.search(
                query,
                method=cfg.ROCCHIO_SEARCH_METHOD,
                top_k=pool_k,
            )
            ranked_ids = [str(r["doc_id"]) for r in ranked]
            added = expand_rocchio(
                q_terms,
                eng.inverted_index,
                eng.N,
                ranked_ids,
                alpha=cfg.ROCCHIO_ALPHA,
                beta=cfg.ROCCHIO_BETA,
                gamma=cfg.ROCCHIO_GAMMA,
                pseudo_relevant_k=cfg.ROCCHIO_PSEUDO_RELEVANT_K,
                pseudo_nonrelevant_k=cfg.ROCCHIO_PSEUDO_NONRELEVANT_K,
                expansion_terms=cfg.ROCCHIO_EXPANSION_TERMS,
                clip_negatives=cfg.ROCCHIO_CLIP_NEGATIVES,
            )
        elif method == "association":
            self._ensure_doc_stats()
            added = expand_association(
                q_terms,
                eng.inverted_index,
                self._doc_terms,  # type: ignore[arg-type]
                self._df,  # type: ignore[arg-type]
                top_m=cfg.ASSOC_TOP_M,
                max_total_terms=cfg.ASSOC_MAX_TOTAL_TERMS,
            )
        elif method == "metric":
            self._ensure_metric()
            added = expand_metric(
                q_terms,
                self._metric_root,  # type: ignore[arg-type]
                self._metric_members,  # type: ignore[arg-type]
                sibling_terms=cfg.METRIC_SIBLING_TERMS,
            )
        else:
            self._ensure_scalar()
            added = expand_scalar(
                q_terms,
                self._scalar_term_cluster,  # type: ignore[arg-type]
                self._scalar_members,  # type: ignore[arg-type]
                sibling_terms=cfg.SCALAR_SIBLING_TERMS,
            )

        expanded_terms = list(q_terms) + added
        expanded_query = " ".join(expanded_terms)
        documents = eng.search(
            expanded_query,
            method=cfg.ROCCHIO_SEARCH_METHOD,
            top_k=cfg.DEFAULT_TOP_K,
        )

        return {
            "original_query": original_joined,
            "expanded_query": expanded_query,
            "method": method,
            "added_terms": added,
            "documents": documents,
        }
