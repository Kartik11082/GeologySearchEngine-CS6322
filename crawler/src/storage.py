import gzip
import json
from pathlib import Path
from typing import Any, Iterable, Iterator

from config import ensure_directories


def _tmp_path(path: Path) -> Path:
    return Path(str(path) + ".tmp")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_directories()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp_path(path)
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
    tmp.replace(path)


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return {} if default is None else default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_gzip_lines(path: Path, lines: Iterable[str]) -> None:
    ensure_directories()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp_path(path)
    with gzip.open(tmp, "wt", encoding="utf-8") as handle:
        for line in lines:
            handle.write(f"{line}\n")
    tmp.replace(path)


def read_gzip_lines(path: Path) -> Iterator[str]:
    if not path.exists():
        return iter(())
    return _read_gzip_lines(path)


def _read_gzip_lines(path: Path) -> Iterator[str]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            value = line.strip()
            if value:
                yield value


def write_jsonl_gz(path: Path, records: Iterable[dict[str, Any]]) -> None:
    ensure_directories()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp_path(path)
    with gzip.open(tmp, "wt", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    tmp.replace(path)


def iter_jsonl_gz(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return iter(())
    return _iter_jsonl_gz(path)


def _iter_jsonl_gz(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            value = line.strip()
            if not value:
                continue
            yield json.loads(value)
