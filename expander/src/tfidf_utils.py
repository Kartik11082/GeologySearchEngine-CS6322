"""TF-IDF weights aligned with indexer relevance.py (log TF + log IDF)."""

from __future__ import annotations

import math


def tfidf_weight(tf: int, df: int, N: int) -> float:
    """Log-weighted TF × IDF (same formula as indexer rank_tfidf)."""
    if tf <= 0 or df <= 0 or N <= 0:
        return 0.0
    return (1.0 + math.log10(tf)) * math.log10(N / df)
