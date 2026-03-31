"""
Relevance client backed by the indexer module (no mock data).
"""

from __future__ import annotations

from .indexer_adapter import search_relevance


def search(query: str, model: str = "vector") -> dict:
    """
    Search indexed documents through the requested model.

    Parameters
    ----------
    query : str
        User search query.
    model : str
        One of: vector, pagerank, hits, combined.
    """
    return search_relevance(query=query, model=model, top_k=10)
