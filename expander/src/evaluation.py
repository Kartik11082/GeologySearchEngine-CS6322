"""
Offline evaluation (Rocchio / cluster query sets). Stub until queries are populated.

Usage (when query files exist):
  python evaluation.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import expander_config as cfg


def main() -> None:
    rq = cfg.QUERIES_DIR / "rocchio_queries.json"
    cq = cfg.QUERIES_DIR / "cluster_queries.json"
    missing = [str(p) for p in (rq, cq) if not p.exists()]
    if missing:
        print(
            "Evaluation skipped: missing query files:\n  "
            + "\n  ".join(missing)
            + "\nPopulate JSON per expander plan; live API works without these."
        )
        sys.exit(0)
    print("Query files found; full evaluation pipeline not implemented yet.")
    sys.exit(0)


if __name__ == "__main__":
    main()
