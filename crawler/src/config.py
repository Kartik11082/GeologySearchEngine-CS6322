from pathlib import Path

TARGET_PAGES = 100_000
MAX_DEPTH = 8
CONCURRENCY = 1
PER_DOMAIN_DELAY = 1.0

REQUEST_TIMEOUT_CONNECT = 5
REQUEST_TIMEOUT_READ = 20
MAX_RETRIES = 3
BACKOFF_BASE = 0.5

MAX_OUTLINKS_PER_PAGE = 200
BATCH_SIZE = 5000
MIN_TEXT_CHARS = 200
GEOLOGY_THRESHOLD = 2
PRIORITY_SCORE_THRESHOLD = 4

USER_AGENT = (
    "GeologyCrawler/1.0 (Zafeer Rangoonwala; ZXR240004; course project)"
)

TRACKING_PARAM_PREFIXES = ("utm_",)
DROP_QUERY_PARAMS = {
    "gclid",
    "fbclid",
    "msclkid",
    "yclid",
    "mc_cid",
    "mc_eid",
}

GEOLOGY_KEYWORDS = [
    "geology",
    "sedimentary",
    "igneous",
    "metamorphic",
    "stratigraphy",
    "tectonic",
    "mineral",
    "volcano",
    "earthquake",
    "petrology",
    "geochronology",
    "fault",
    "plate tectonics",
]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
BATCHES_DIR = DATA_DIR / "batches"
SEEN_DIR = DATA_DIR / "seen"
LOGS_DIR = DATA_DIR / "logs"

SEEDS_PATH = PROJECT_ROOT / "seeds.txt"

VISITED_URLS_PATH = SEEN_DIR / "visited_urls.txt.gz"
CONTENT_HASHES_PATH = SEEN_DIR / "content_hashes.txt.gz"
FRONTIER_CHECKPOINT_PATH = SEEN_DIR / "frontier_checkpoint.jsonl.gz"
STATE_PATH = SEEN_DIR / "crawler_state.json"
LOG_PATH = LOGS_DIR / "crawler.log"


def ensure_directories() -> None:
    BATCHES_DIR.mkdir(parents=True, exist_ok=True)
    SEEN_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
