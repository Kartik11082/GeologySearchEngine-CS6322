import time
from pathlib import Path
from typing import Any

from config import BATCHES_DIR
from storage import write_json, write_jsonl_gz


def export_batch(
    batch_idx: int,
    pages: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    stats: dict[str, int],
    timings: dict[str, float],
) -> dict[str, str]:
    BATCHES_DIR.mkdir(parents=True, exist_ok=True)
    tag = f"{batch_idx:04d}"

    pages_path = BATCHES_DIR / f"pages_batch_{tag}.jsonl.gz"
    edges_path = BATCHES_DIR / f"edges_batch_{tag}.jsonl.gz"
    metadata_path = BATCHES_DIR / f"metadata_batch_{tag}.json"

    write_jsonl_gz(pages_path, pages)
    write_jsonl_gz(edges_path, edges)
    write_json(
        metadata_path,
        {
            "batch": batch_idx,
            "generated_at": time.time(),
            "pages_in_batch": len(pages),
            "edges_in_batch": len(edges),
            "stats": stats,
            "timings": timings,
        },
    )

    return {
        "pages_path": str(Path(pages_path).resolve()),
        "edges_path": str(Path(edges_path).resolve()),
        "metadata_path": str(Path(metadata_path).resolve()),
    }
