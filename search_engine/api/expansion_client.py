"""
Query expansion client placeholder.

Query expansion/relevance feedback is owned by X5 and is intentionally not
implemented here to avoid synthetic/mock behavior.
"""

from __future__ import annotations

def expand(query: str) -> dict:
    """
    Expand a query and return expanded results.

    Raises
    ------
    NotImplementedError
        Until X5 query-expansion module is integrated.
    """
    raise NotImplementedError(
        "X5 query expansion module is pending integration. "
        "Required: Rocchio + pseudo-relevance feedback (associative/metric/scalar clustering)."
    )
