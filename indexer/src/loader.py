"""Load crawled pages and edges from the crawler batch files."""

import gzip
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from config import CRAWLER_BATCHES_DIR

UTILITY_PATH_KEYWORDS = {
    "about",
    "accessibility",
    "account",
    "admin",
    "careers",
    "comment",
    "comments",
    "contact",
    "cookie",
    "donate",
    "faq",
    "feedback",
    "help",
    "jobs",
    "legal",
    "login",
    "logout",
    "media",
    "newsletter",
    "press",
    "privacy",
    "profile",
    "register",
    "search",
    "signin",
    "signup",
    "subscribe",
    "support",
    "terms",
}

UTILITY_TITLE_KEYWORDS = {
    "contact us",
    "privacy policy",
    "terms of use",
    "terms and conditions",
    "media contacts",
}


def _iter_jsonl_gz(path: Path):
    """Yield each JSON object from a gzipped .jsonl file."""
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def _is_utility_page(record: dict[str, Any]) -> bool:
    """Skip low-value utility pages that hurt result quality."""
    url = (record.get("final_url") or record.get("url") or "").lower()
    title = (record.get("title") or "").lower()

    try:
        parsed = urlsplit(url)
    except ValueError:
        parsed = urlsplit("")

    path_tokens = re.split(r"[/\-_\.]+", parsed.path or "")
    query_tokens = re.split(r"[=&\-_\.]+", parsed.query or "")
    tokens = {token for token in (path_tokens + query_tokens) if token}
    if any(keyword in tokens for keyword in UTILITY_PATH_KEYWORDS):
        return True

    return any(keyword in title for keyword in UTILITY_TITLE_KEYWORDS)


def load_pages(batches_dir: Path = CRAWLER_BATCHES_DIR) -> list[dict[str, Any]]:
    """Read all pages from every pages_batch_*.jsonl.gz file."""
    pages: list[dict[str, Any]] = []
    for path in sorted(batches_dir.glob("pages_batch_*.jsonl.gz")):
        for record in _iter_jsonl_gz(path):
            if _is_utility_page(record):
                continue
            pages.append(record)
    return pages


def load_edges(batches_dir: Path = CRAWLER_BATCHES_DIR) -> list[dict[str, Any]]:
    """Read all edges from every edges_batch_*.jsonl.gz file."""
    edges: list[dict[str, Any]] = []
    for path in sorted(batches_dir.glob("edges_batch_*.jsonl.gz")):
        for record in _iter_jsonl_gz(path):
            edges.append(record)
    return edges


def build_url_to_docid(pages: list[dict[str, Any]]) -> dict[str, int]:
    """Map every URL (original + final) to its doc_id for graph resolution."""
    mapping: dict[str, int] = {}
    for page in pages:
        doc_id = page["doc_id"]
        mapping[page["url"]] = doc_id
        if page.get("final_url"):
            mapping[page["final_url"]] = doc_id
    return mapping


if __name__ == "__main__":
    pages = load_pages()
    edges = load_edges()
    url_map = build_url_to_docid(pages)
    print(f"Loaded {len(pages)} pages, {len(edges)} edges, {len(url_map)} URL mappings")
