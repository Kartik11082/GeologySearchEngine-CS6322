"""
Query expansion (X5): delegates to expander.QueryExpander with a process-wide singleton.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_EXPANDER_SRC = _PROJECT_ROOT / "expander" / "src"

_EXPANDER_INSTANCE = None
_EXPANDER_LOCK = threading.Lock()


def _get_expander():
    global _EXPANDER_INSTANCE
    if _EXPANDER_INSTANCE is not None:
        return _EXPANDER_INSTANCE
    with _EXPANDER_LOCK:
        if _EXPANDER_INSTANCE is None:
            if str(_EXPANDER_SRC) not in sys.path:
                sys.path.insert(0, str(_EXPANDER_SRC))
            from expander import QueryExpander

            _EXPANDER_INSTANCE = QueryExpander()
        return _EXPANDER_INSTANCE


def expand(query: str, method: str = "rocchio") -> dict:
    """
    Expand a query and return ranked documents.

    Returns
    -------
    dict with keys: original_query, expanded_query, method, documents
    (optional added_terms for debugging)
    """
    qe = _get_expander()
    return qe.expand(query, method=method)
