"""
Geology Search Engine — Integration Layer
==========================================
FastAPI backend that integrates available modules (X2 relevance, X3 UI
comparisons) and explicitly reports pending modules (X4 clustering, X5
query expansion) without using mock data.

Run (use conda env ``nlp``):
    conda activate nlp
    cd search_engine
    pip install -r ../indexer/requirements.txt -r requirements.txt
    python main.py
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------------------------
# Load .env file (stdlib only — no python-dotenv dependency)
# ---------------------------------------------------------------------------
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

from api import relevance_client, clustering_client, expansion_client, external_search

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Geology Search Engine",
    description="Unified search across relevance models, clustering, query expansion, and external engines.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keep local development on a single origin so localhost and 127.0.0.1
# do not behave like two separate sites (separate cache/cookies/history).
_LOCAL_HOST_ALIASES = {"localhost", "127.0.0.1"}
_CANONICAL_LOCAL_HOST = os.environ.get("CANONICAL_LOCAL_HOST", "localhost").lower()


@app.middleware("http")
async def canonical_local_origin(request: Request, call_next):
    host_header = request.headers.get("host", "")
    host_name = host_header.split(":", 1)[0].lower()

    if host_name in _LOCAL_HOST_ALIASES and host_name != _CANONICAL_LOCAL_HOST:
        port = request.url.port
        netloc = f"{_CANONICAL_LOCAL_HOST}:{port}" if port else _CANONICAL_LOCAL_HOST
        redirect_url = request.url.replace(netloc=netloc)
        return RedirectResponse(url=str(redirect_url), status_code=307)

    return await call_next(request)


# ---------------------------------------------------------------------------
# Query log (in-memory + disk persistence)
# ---------------------------------------------------------------------------
_query_log: list[dict[str, Any]] = []
_LOG_FILE = Path(__file__).parent / "query_log.jsonl"


def _log_query(query: str, method: str, elapsed_sec: float) -> None:
    entry = {
        "query": query,
        "method": method,
        "elapsed_sec": round(elapsed_sec, 4),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _query_log.append(entry)
    with open(_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# API Routes (matches the docx frontend contract)
# ---------------------------------------------------------------------------


@app.get("/api/search")
async def search(q: str = Query(...), method: str = Query(default="vector")):
    """
    Section 1 — Relevance model results.
    Returns time, model name, and ranked document list.
    """
    q = q.strip()
    method = method.strip().lower()
    if not q:
        return JSONResponse(
            status_code=400, content={"error": "Query cannot be empty."}
        )

    start = time.perf_counter()
    try:
        data = relevance_client.search(q, method)
    except Exception as e:
        data = {"source": method, "documents": [], "error": str(e)}

    elapsed = time.perf_counter() - start
    _log_query(q, method, elapsed)

    # Reshape to match frontend contract
    docs = data.get("documents", [])
    model_label = {
        "vector": "TF-IDF",
        "pagerank": "PageRank",
        "hits": "HITS Authority",
        "combined": "Hybrid Ensemble",
    }.get(method, method.upper())

    return {
        "time": round(elapsed, 3),
        "model": model_label,
        "results": docs,
    }


@app.get("/api/clusters")
async def clusters(q: str = Query(...)):
    """
    Section 2 — Clustered results.
    Returns cluster definitions and results tagged with cluster IDs.
    """
    q = q.strip()
    if not q:
        return JSONResponse(
            status_code=400, content={"error": "Query cannot be empty."}
        )

    try:
        raw_clusters = clustering_client.get_clusters(q)
    except NotImplementedError as e:
        return {
            "available": False,
            "owner": "X4",
            "message": str(e),
            "required": [
                "Flat clustering over crawled collection",
                "Two agglomerative clustering methods",
                "Cluster-enhanced relevance output contract",
            ],
            "clusters": [],
            "results": [],
        }
    except Exception as e:
        return {"clusters": [], "results": [], "error": str(e)}

    # Fixed cluster color palette
    palette = [
        "#C8A96E",
        "#5EC4B0",
        "#8B78E8",
        "#4285F4",
        "#00B4D8",
        "#E05C5C",
        "#81b29a",
        "#f2cc8f",
    ]

    cluster_defs = []
    all_results = []
    for i, c in enumerate(raw_clusters):
        cid = c.get("cluster_label", f"cluster_{i}").lower().replace(" ", "_")
        color = palette[i % len(palette)]
        docs = c.get("documents", [])
        cluster_defs.append(
            {
                "id": cid,
                "name": c.get("cluster_label", f"Cluster {i}"),
                "color": color,
                "count": len(docs),
            }
        )
        for doc in docs:
            doc_copy = dict(doc)
            doc_copy["cluster"] = cid
            all_results.append(doc_copy)

    return {"available": True, "clusters": cluster_defs, "results": all_results}


@app.get("/api/expand")
async def expand(
    q: str = Query(...),
    method: str = Query(default="rocchio"),
):
    """
    Section 3 — Query expansion.
    Returns original terms, added terms, and expanded results.
    method: rocchio | association | metric | scalar
    """
    q = q.strip()
    method = (method or "rocchio").strip().lower()
    if not q:
        return JSONResponse(
            status_code=400, content={"error": "Query cannot be empty."}
        )

    try:
        data = expansion_client.expand(q, method=method)
    except NotImplementedError as e:
        return {
            "available": False,
            "owner": "X5",
            "message": str(e),
            "required": [
                "Rocchio relevance feedback on judged queries",
                "Pseudo-relevance feedback on large query set",
                "Associative, metric, and scalar cluster-based expansion",
            ],
            "original": q.split(),
            "added": [],
            "results": [],
        }
    except Exception as e:
        return {"original": q.split(), "added": [], "results": [], "error": str(e)}

    original_terms = data.get("original_query", q).split()
    expanded_terms = data.get("expanded_query", q).split()
    added_terms = [
        t
        for t in expanded_terms
        if t.lower() not in {w.lower() for w in original_terms}
    ]

    return {
        "available": True,
        "original": original_terms,
        "added": added_terms,
        "results": data.get("documents", []),
    }


@app.get("/api/capabilities")
async def capabilities():
    """Advertise which project modules are currently integrated."""
    return {
        "relevance": {
            "available": True,
            "owner": "X2",
            "models": ["vector", "pagerank", "hits", "combined"],
            "source": "indexer",
        },
        "clustering": {"available": False, "owner": "X4"},
        "expansion": {
            "available": True,
            "owner": "X5",
            "methods": ["rocchio", "association", "metric", "scalar"],
        },
        "comparison": {"available": True, "owner": "X3"},
    }


@app.get("/api/compare")
async def compare(q: str = Query(...)):
    """
    Section 4 — Google/Bing comparison.
    Returns Google Custom Search results when configured; otherwise returns redirect URLs with fallback info.
    """
    q = q.strip()
    if not q:
        return JSONResponse(
            status_code=400, content={"error": "Query cannot be empty."}
        )

    google_data = external_search.google(q)
    bing_data = external_search.bing(q)

    return {
        "google": google_data,
        "bing": bing_data,
    }


@app.get("/api/logs")
async def get_logs(limit: int = Query(default=50, le=500)):
    """Return the most recent query log entries."""
    return {"logs": _query_log[-limit:], "total": len(_query_log)}


# ---------------------------------------------------------------------------
# Serve frontend static files
# ---------------------------------------------------------------------------
FRONTEND_DIR = Path(__file__).parent / "frontend"


@app.get("/")
async def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")


# Mount static files AFTER explicit routes so they don't shadow /api/*
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    print("\n  Geology Search Engine running at http://localhost:8000\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
