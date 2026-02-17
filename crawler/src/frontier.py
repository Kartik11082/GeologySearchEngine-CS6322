from collections import deque
from dataclasses import asdict, dataclass

from config import MAX_DEPTH, PRIORITY_SCORE_THRESHOLD
from storage import iter_jsonl_gz, write_jsonl_gz


@dataclass(slots=True)
class FrontierItem:
    url: str
    depth: int
    score: int
    discovered_from: int | None


class Frontier:
    def __init__(
        self,
        max_depth: int = MAX_DEPTH,
        priority_score: int = PRIORITY_SCORE_THRESHOLD,
        dedup_store=None,
    ) -> None:
        self.max_depth = max_depth
        self.priority_score = priority_score
        self.dedup_store = dedup_store
        self._high: deque[FrontierItem] = deque()
        self._normal: deque[FrontierItem] = deque()
        self._queued_urls: set[str] = set()

    def push(self, item: FrontierItem) -> bool:
        if not item.url:
            return False
        if item.depth > self.max_depth:
            return False
        if item.url in self._queued_urls:
            return False
        if self.dedup_store is not None and self.dedup_store.seen_url(item.url):
            return False

        queue = self._high if item.score >= self.priority_score else self._normal
        queue.append(item)
        self._queued_urls.add(item.url)
        return True

    def pop(self) -> FrontierItem | None:
        item = None
        if self._high:
            item = self._high.popleft()
        elif self._normal:
            item = self._normal.popleft()
        if item is not None:
            self._queued_urls.discard(item.url)
        return item

    def __len__(self) -> int:
        return len(self._high) + len(self._normal)

    def snapshot(self, path) -> None:
        def _records():
            for item in self._high:
                record = asdict(item)
                record["queue"] = "high"
                yield record
            for item in self._normal:
                record = asdict(item)
                record["queue"] = "normal"
                yield record

        write_jsonl_gz(path, _records())

    def restore(self, path) -> int:
        if len(self) > 0:
            return len(self)

        restored = 0
        for record in iter_jsonl_gz(path):
            item = FrontierItem(
                url=record.get("url", ""),
                depth=int(record.get("depth", 0)),
                score=int(record.get("score", 0)),
                discovered_from=record.get("discovered_from"),
            )
            if not item.url or item.depth > self.max_depth:
                continue
            if item.url in self._queued_urls:
                continue
            queue_name = record.get("queue", "normal")
            queue = self._high if queue_name == "high" else self._normal
            queue.append(item)
            self._queued_urls.add(item.url)
            restored += 1
        return restored
