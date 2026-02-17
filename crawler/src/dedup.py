import hashlib

from config import CONTENT_HASHES_PATH, VISITED_URLS_PATH
from storage import read_gzip_lines, write_gzip_lines


def content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()


class DedupStore:
    def __init__(
        self,
        visited_urls_path=VISITED_URLS_PATH,
        content_hashes_path=CONTENT_HASHES_PATH,
    ) -> None:
        self.visited_urls_path = visited_urls_path
        self.content_hashes_path = content_hashes_path
        self.visited_urls: set[str] = set()
        self.content_hashes: set[str] = set()

    def seen_url(self, url: str) -> bool:
        return url in self.visited_urls

    def mark_url(self, url: str) -> None:
        self.visited_urls.add(url)

    def seen_content(self, hash_value: str) -> bool:
        return hash_value in self.content_hashes

    def mark_content(self, hash_value: str) -> None:
        self.content_hashes.add(hash_value)

    def snapshot(self) -> None:
        write_gzip_lines(self.visited_urls_path, sorted(self.visited_urls))
        write_gzip_lines(self.content_hashes_path, sorted(self.content_hashes))

    def restore(self) -> dict[str, int]:
        self.visited_urls = set(read_gzip_lines(self.visited_urls_path))
        self.content_hashes = set(read_gzip_lines(self.content_hashes_path))
        return {
            "visited_urls": len(self.visited_urls),
            "content_hashes": len(self.content_hashes),
        }
