"""Paths and default hyperparameters for the query expander (X5).

Named expander_config to avoid shadowing indexer/src/config.py when cwd is expander/src.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INDEXER_SRC = PROJECT_ROOT / "indexer" / "src"

EXPANDER_ROOT = Path(__file__).resolve().parents[1]
EXPANDER_DATA_DIR = EXPANDER_ROOT / "data"
EXPANDER_RESULTS_DIR = EXPANDER_ROOT / "results"
QUERIES_DIR = EXPANDER_ROOT / "queries"

# Vocabulary pruning (for cluster precompute)
MIN_DF = 2
MAX_DF_RATIO = 0.85

# Rocchio (pseudo-relevance feedback, v1)
ROCCHIO_ALPHA = 1.0
ROCCHIO_BETA = 0.75
ROCCHIO_GAMMA = 0.15
ROCCHIO_PSEUDO_RELEVANT_K = 10
ROCCHIO_PSEUDO_NONRELEVANT_K = 5
ROCCHIO_EXPANSION_TERMS = 8
ROCCHIO_CLIP_NEGATIVES = True
ROCCHIO_FETCH_POOL = 80
ROCCHIO_SEARCH_METHOD = "bm25"

# Association expansion
ASSOC_TOP_M = 5
ASSOC_MAX_TOTAL_TERMS = 12

# Metric clusters (union-find on cosine edges within documents)
METRIC_SIM_THRESHOLD = 0.12
METRIC_MAX_TERMS_PER_DOC = 100
METRIC_SIBLING_TERMS = 8

# Scalar single-pass clusters
SCALAR_DOT_THRESHOLD = 0.08
SCALAR_MAX_CLUSTER_SIZE = 80
SCALAR_SIBLING_TERMS = 8
SCALAR_PASS_ORDER = "idf_desc"  # idf_desc | df_asc

DEFAULT_TOP_K = 10

VALID_METHODS = frozenset({"rocchio", "association", "metric", "scalar"})
