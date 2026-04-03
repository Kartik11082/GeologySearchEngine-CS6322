"""
Hyperparameter tuning (random search + Optuna). Stub until query sets exist.

Usage:
  python tuning.py
"""

from __future__ import annotations

import sys

import expander_config as cfg


def main() -> None:
    if not cfg.QUERIES_DIR.exists():
        print("Tuning skipped: queries directory missing.")
        sys.exit(0)
    rq = cfg.QUERIES_DIR / "rocchio_queries.json"
    cq = cfg.QUERIES_DIR / "cluster_queries.json"
    if not rq.exists() and not cq.exists():
        print(
            "Tuning skipped: add rocchio_queries.json and/or cluster_queries.json first."
        )
        sys.exit(0)
    print("Tuning pipeline (Optuna) not implemented yet.")
    sys.exit(0)


if __name__ == "__main__":
    main()
