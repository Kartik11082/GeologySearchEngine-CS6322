import argparse
import logging
import time
from pathlib import Path
from typing import Any

from config import (
    BATCH_SIZE,
    FRONTIER_CHECKPOINT_PATH,
    GEOLOGY_THRESHOLD,
    LOG_PATH,
    MAX_OUTLINKS_PER_PAGE,
    MIN_TEXT_CHARS,
    SEEDS_PATH,
    STATE_PATH,
    TARGET_PAGES,
    ensure_directories,
)
from dedup import DedupStore, content_hash
from export import export_batch
from fetcher import create_session, fetch_url
from frontier import Frontier, FrontierItem
from parser import parse_html
from robots import RobotsManager
from storage import read_json, write_json
from utils import (
    geology_score,
    is_utility_title,
    is_utility_url,
    link_priority_score,
    normalize_url,
)

COUNTER_KEYS = [
    "discovered",
    "attempted",
    "fetched_200",
    "parsed",
    "kept_after_dedup",
    "kept_after_quality",
    "final_usable",
    "duplicates_url",
    "duplicates_content",
    "blocked_robots",
    "filtered_utility_pages",
    "filtered_utility_outlinks",
    "non_html",
    "errors",
]


def _default_stats() -> dict[str, int]:
    return {key: 0 for key in COUNTER_KEYS}


def _setup_logger() -> logging.Logger:
    logger = logging.getLogger("geology_crawler")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def _resolve_seeds_path(seeds_path: str) -> Path:
    path = Path(seeds_path)
    if path.is_absolute():
        return path
    candidate = (SEEDS_PATH.parent / path).resolve()
    if candidate.exists():
        return candidate
    return path.resolve()


def _load_seeds(seeds_path: str) -> list[str]:
    path = _resolve_seeds_path(seeds_path)
    if not path.exists():
        return []

    seeds: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            normalized = normalize_url(line)
            if normalized:
                seeds.append(normalized)
    return seeds


def _load_crawler_state() -> dict[str, Any]:
    state = read_json(STATE_PATH, default={})
    stats = _default_stats()
    stats.update(state.get("stats", {}))
    return {
        "next_doc_id": int(state.get("next_doc_id", 1)),
        "next_batch_idx": int(state.get("next_batch_idx", 1)),
        "crawl_start_ts": float(state.get("crawl_start_ts", time.time())),
        "stats": stats,
    }


def _persist_crawler_state(
    next_doc_id: int,
    next_batch_idx: int,
    crawl_start_ts: float,
    stats: dict[str, int],
) -> None:
    write_json(
        STATE_PATH,
        {
            "next_doc_id": next_doc_id,
            "next_batch_idx": next_batch_idx,
            "crawl_start_ts": crawl_start_ts,
            "stats": stats,
            "saved_at": time.time(),
        },
    )


def main(seeds_path: str = "seeds.txt") -> None:
    ensure_directories()
    logger = _setup_logger()

    state = _load_crawler_state()
    stats = state["stats"]
    next_doc_id = state["next_doc_id"]
    next_batch_idx = state["next_batch_idx"]
    crawl_start_ts = state["crawl_start_ts"]

    session = create_session()
    dedup_store = DedupStore()
    restore_counts = dedup_store.restore()

    frontier = Frontier(dedup_store=dedup_store)
    restored_frontier_count = frontier.restore(FRONTIER_CHECKPOINT_PATH)

    logger.info(
        "Restored state | visited=%d content_hashes=%d frontier=%d usable=%d",
        restore_counts["visited_urls"],
        restore_counts["content_hashes"],
        restored_frontier_count,
        stats["final_usable"],
    )

    if len(frontier) == 0 and stats["final_usable"] < TARGET_PAGES:
        for seed in _load_seeds(seeds_path):
            added = frontier.push(
                FrontierItem(url=seed, depth=0, score=0, discovered_from=None)
            )
            if added:
                stats["discovered"] += 1
        logger.info("Seeded frontier with %d URLs", len(frontier))

    robots = RobotsManager(session=session)

    pages_buffer: list[dict[str, Any]] = []
    edges_buffer: list[dict[str, Any]] = []
    batch_start_ts = time.time()

    def flush_batch(force: bool = False) -> None:
        nonlocal next_batch_idx, batch_start_ts
        if not pages_buffer and not force:
            return

        timings = {
            "crawl_elapsed_sec": time.time() - crawl_start_ts,
            "batch_elapsed_sec": time.time() - batch_start_ts,
        }
        paths = export_batch(
            batch_idx=next_batch_idx,
            pages=pages_buffer,
            edges=edges_buffer,
            stats=dict(stats),
            timings=timings,
        )

        logger.info(
            "Exported batch %04d | pages=%d edges=%d | usable=%d",
            next_batch_idx,
            len(pages_buffer),
            len(edges_buffer),
            stats["final_usable"],
        )
        logger.info(
            "Batch files | pages=%s | edges=%s | metadata=%s",
            paths["pages_path"],
            paths["edges_path"],
            paths["metadata_path"],
        )

        pages_buffer.clear()
        edges_buffer.clear()
        next_batch_idx += 1
        batch_start_ts = time.time()

        dedup_store.snapshot()
        frontier.snapshot(FRONTIER_CHECKPOINT_PATH)
        _persist_crawler_state(next_doc_id, next_batch_idx, crawl_start_ts, stats)

    try:
        while len(frontier) > 0 and stats["final_usable"] < TARGET_PAGES:
            item = frontier.pop()
            if item is None:
                break

            if dedup_store.seen_url(item.url):
                stats["duplicates_url"] += 1
                continue

            dedup_store.mark_url(item.url)
            stats["attempted"] += 1

            if not robots.is_allowed(item.url):
                stats["blocked_robots"] += 1
                continue

            robots.wait_if_needed(item.url)

            fetched = fetch_url(session, item.url)
            if fetched.error:
                stats["errors"] += 1
                continue

            if fetched.status != 200:
                continue
            stats["fetched_200"] += 1

            if not fetched.html:
                stats["non_html"] += 1
                continue

            try:
                parsed = parse_html(fetched.html, fetched.final_url or item.url)
            except Exception:
                stats["errors"] += 1
                continue

            stats["parsed"] += 1
            if len(parsed.clean_text) < MIN_TEXT_CHARS:
                continue

            source_url = normalize_url(fetched.final_url or item.url) or (fetched.final_url or item.url)
            if is_utility_url(source_url) or is_utility_title(parsed.title):
                stats["filtered_utility_pages"] += 1
                continue

            score = geology_score(
                parsed.title,
                parsed.clean_text,
                source_url,
            )
            if score < GEOLOGY_THRESHOLD:
                continue
            stats["kept_after_quality"] += 1

            hash_value = content_hash(parsed.clean_text)
            if dedup_store.seen_content(hash_value):
                stats["duplicates_content"] += 1
                continue
            dedup_store.mark_content(hash_value)
            stats["kept_after_dedup"] += 1

            doc_id = next_doc_id
            next_doc_id += 1
            stats["final_usable"] += 1

            pages_buffer.append(
                {
                    "doc_id": doc_id,
                    "url": item.url,
                    "final_url": source_url,
                    "title": parsed.title,
                    "clean_text": parsed.clean_text,
                    "fetch_time": time.time(),
                    "status": fetched.status,
                    "depth": item.depth,
                    "geology_score": score,
                    "content_type": fetched.content_type,
                }
            )

            kept_outlinks: list[str] = []
            for target_url in parsed.outlinks:
                if is_utility_url(target_url):
                    stats["filtered_utility_outlinks"] += 1
                    continue
                kept_outlinks.append(target_url)
                edges_buffer.append(
                    {
                        "source_doc_id": doc_id,
                        "source_url": source_url,
                        "target_url": target_url,
                        "anchor_text": parsed.anchor_map.get(target_url, ""),
                    }
                )

            for target_url in kept_outlinks[:MAX_OUTLINKS_PER_PAGE]:
                anchor_text = parsed.anchor_map.get(target_url, "")
                priority_score = link_priority_score(score, anchor_text, target_url)
                added = frontier.push(
                    FrontierItem(
                        url=target_url,
                        depth=item.depth + 1,
                        score=priority_score,
                        discovered_from=doc_id,
                    )
                )
                if added:
                    stats["discovered"] += 1

            if len(pages_buffer) >= BATCH_SIZE:
                flush_batch()
    except KeyboardInterrupt:
        logger.info("Interrupted by user; exporting current buffers.")
    finally:
        if pages_buffer:
            flush_batch()
        dedup_store.snapshot()
        frontier.snapshot(FRONTIER_CHECKPOINT_PATH)
        _persist_crawler_state(next_doc_id, next_batch_idx, crawl_start_ts, stats)
        session.close()
        logger.info(
            "Crawler stopped | usable=%d attempted=%d remaining_frontier=%d",
            stats["final_usable"],
            stats["attempted"],
            len(frontier),
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Geology crawler entrypoint")
    parser.add_argument(
        "--seeds",
        default="seeds.txt",
        help="Path to seeds file (default: seeds.txt)",
    )
    args = parser.parse_args()
    main(seeds_path=args.seeds)
