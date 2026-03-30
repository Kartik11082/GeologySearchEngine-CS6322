"""
Query Expansion Client (X5 Interface)
--------------------------------------
Stub that returns a mock expanded query and its results.
When teammates deliver X5, replace `expand()` body with real call.
"""

from __future__ import annotations

from .relevance_client import search as relevance_search

# Simple expansion map — maps common geology terms to expanded versions
_EXPANSION_MAP: dict[str, str] = {
    "earthquake": "earthquake seismic tremor fault tectonic plate",
    "volcano": "volcano volcanic eruption magma lava pyroclastic",
    "mineral": "mineral crystal silicate oxide sulfide hardness",
    "rock": "rock igneous sedimentary metamorphic petrology lithology",
    "tectonic": "tectonic plate convergent divergent transform subduction",
    "fossil": "fossil paleontology stratigraphy biostratigraphy fauna",
    "erosion": "erosion weathering sediment transport deposition",
    "fault": "fault fracture normal reverse strike-slip seismic",
    "magma": "magma melt crystallization igneous intrusion extrusion",
    "sediment": "sediment deposition diagenesis lithification clastic",
}


def expand(query: str) -> dict:
    """
    Expand a query and return expanded results.

    Parameters
    ----------
    query : str
        Original user query.

    Returns
    -------
    dict with keys:
        original_query  — the input query
        expanded_query  — the expanded version
        documents       — ranked results for the expanded query
    """
    # --- STUB: replace with real X5 call ---
    query_lower = query.lower().strip()
    terms = query_lower.split()

    expanded_parts = []
    for term in terms:
        if term in _EXPANSION_MAP:
            expanded_parts.append(_EXPANSION_MAP[term])
        else:
            expanded_parts.append(term)

    expanded_query = " ".join(expanded_parts)

    # Re-search with expanded query through the relevance engine
    results = relevance_search(expanded_query, model="combined")

    return {
        "original_query": query,
        "expanded_query": expanded_query,
        "documents": results["documents"],
    }
