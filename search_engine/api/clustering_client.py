"""
Clustering client placeholder.

Clustering (flat + agglomerative) is owned by X4 and is intentionally not
implemented here to avoid synthetic/mock behavior.
"""

from __future__ import annotations

def get_clusters(query: str) -> list[dict]:
    """
    Return clustered results.

    Raises
    ------
    NotImplementedError
        Until X4 clustering module is integrated.
    """
    raise NotImplementedError(
        "X4 clustering module is pending integration. "
        "Required: flat clustering + two agglomerative methods over crawled pages."
    )
